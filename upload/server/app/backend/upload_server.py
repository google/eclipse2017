#
# Copyright 2016 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from datetime import datetime
import hashlib
import imghdr
import json
import os
import threading
import time
import tempfile
import zipfile
import shutil
from uuid import uuid4
import StringIO
import io

import flask
from google.cloud import datastore
from google.gax.errors import GaxError
from werkzeug.exceptions import ClientDisconnected

from common import config
from common import constants
from common import datastore_schema as ds
from common.eclipse2017_exceptions import FailedToRenameFileError
from common.eclipse2017_exceptions import FailedToSaveToDatastoreError
from common.exif import _extract_exif_metadata
from common import users
from common import roles
from common import flask_users
from common import util

VALID_MEGAMOVIE_UPLOADER_ROLES = set([roles.VOLUNTEER_ROLE])
VALID_TERAMOVIE_UPLOADER_ROLES = set([roles.USER_ROLE])

class UploadServer(flask.Flask):
    """
    Upload server application
    """
    def __init__(self, project_id, session_enc_key,
                 google_oauth2_client_id,
                 google_oauth2_client_secret,
                 file_not_ready_suffix, directory, datastore_kind,
                 user_datastore_kind, retrys, datastore=datastore,
                 datetime=datetime, os=os, request=flask.request,
                 Response=flask.Response,
                 threading=threading,
                 time=time, util=util, **kwargs):
        super(UploadServer, self).__init__(__name__, **kwargs)
        # Dependency injection
        self.datastore = datastore
        self.datetime = datetime
        self.os = os
        self.session = flask.session
        self.redirect = flask.redirect
        self.url_for = flask.url_for
        self.threading = threading
        self.time = time
        self.request = request
        self.Response = Response
        self.util = util

        self._file_not_ready_suffix = file_not_ready_suffix
        self._datastore_kind = datastore_kind
        self._user_datastore_kind = user_datastore_kind
        self._retrys = retrys

        # Shared directory, accessible by both the upload server and upload
        # daemon containers. Dies with the pod that contains the upload
        # server/daemon
        self._dir = directory

        self.config['PROJECT_ID'] = project_id
        self.config['SECRET_KEY'] = session_enc_key
        self.config['GOOGLE_OAUTH2_CLIENT_ID'] = google_oauth2_client_id
        self.config['GOOGLE_OAUTH2_CLIENT_SECRET'] = google_oauth2_client_secret
        self.debug = False

        self.add_url_rule('/', 'upload', self.upload, methods=('POST', ))

        self.add_url_rule('/healthz', 'healthz', self.health_check)
        self.add_url_rule('/ready', 'ready', self.ready)

    def health_check(self):
        """
        Upload server health endpoint.
        TODO: make this useful.
        """
        return self.Response('OK', status=constants.HTTP_OK)

    def ready(self):
        """
        Readiness check.
        """
        return self.Response('OK', status=constants.HTTP_OK)

    def upload(self):
        """
        Upload request endpoint.
        If accessed via GET, returns an upload form.
        If accessed via POST, handles a file upload.
        TODO: make this protected by oauth2.
        """
        return self._upload_post()

    def _upload_post(self):
        """
        Request handler for upload POST requests. Writes accepts files in POST
        request body and saves them to the local file system as
        <self._dir>/<uuid>.<file extension as uploaded>
        Creates datastore record for uploaded files and indicates that they
        have yet to be uploaded to Cloud Storage.
        Returns constants.HTTP_ERROR status if an error occurs with a
            short message.
        Returns constants.HTTP_OK response on success with no message.
        Returns constants.HTTP_OOM status if the server is under too much
            load to handle the request.
        """
        self.logger.info("Upload POST received")
        datastore_client = self.datastore.Client(self.config['PROJECT_ID'])

        # Fetch the user's identifier from the request, which
        # contains the oauth2 creds.
        try:
            token = flask.request.headers['X-IDTOKEN']
        except Exception as e:
            self.logger.error("Missing credential token header")
            return flask.Response('Missing credential token header', 405)
        try:
            upload_session_id = flask.request.headers['X-UPLOADSESSIONID']
        except Exception as e:
            self.logger.error("Missing session ID")
            return flask.Response('Missing session ID', 400)
        try:
            image_bucket = flask.request.headers['X-IMAGE-BUCKET']
        except Exception as e:
            self.logger.error("Missing image bucket")
            return flask.Response('Missing image bucket', 400)

        try:
            cc0_agree = flask.request.headers['X-CC0-AGREE']
            if cc0_agree != 'true':
                raise ValueError('Must accept cc0')
        except Exception as e:
            self.logger.error("Missing CC0 agreement")
            return flask.Response('Missing CC0 agreement', 400)

        try:
            public_agree = flask.request.headers['X-PUBLIC-AGREE']
            if public_agree != 'true':
                raise ValueError('Must accept public database')
        except Exception as e:
            self.logger.error("Missing public dataset agreement")
            return flask.Response('Missing public dataset agreement', 400)

        # TODO(dek): read and update hashlib object using fix-sized buffers to avoid memory blowup
        # Read the content of the upload completely, before returning an error.
        file_ = flask.request.files['file']
        original_filename = file_.filename
        self.logger.info("Reading upload stream")
        content = file_.stream.read()
        self.logger.info("Read upload stream")

        result = flask_users.authn_check(flask.request.headers)
        if isinstance(result, flask.Response):
            self.logger.error("Failed auth check")
            return result
        userid_hash = users.get_userid_hash(result)
        if not users.check_if_user_exists(datastore_client, userid_hash):
            self.logger.error("Failed profile check")
            return self.Response('Profile required to upload images.', status=400)
        r = roles.get_user_role(datastore_client, userid_hash)

        # Check for a valid bucket.
        valid_bucket = False
        if image_bucket == 'app':
            valid_bucket = True
        elif image_bucket == 'megamovie' or image_bucket == 'volunteer_test':
            valid_bucket = self._check_role_in_roles(r, VALID_MEGAMOVIE_UPLOADER_ROLES)
        elif image_bucket == 'teramovie':
            valid_bucket = self._check_role_in_roles(r, VALID_TERAMOVIE_UPLOADER_ROLES)
        else:
            # Not a known bucket.
            valid_bucket = False

        if not valid_bucket:
            self.logger.error("Failed bucket check")
            return self.Response('Valid role required to upload images to this bucket, or bucket is unknown', status=400)

        content_type = self.request.content_type

        name = hashlib.sha256(content).hexdigest()
        self.logger.info("Received image with digest: %s" % name)
        # Local file system file paths
        local_file = self.os.path.join(self._dir, name)
        temp_file = local_file + self._file_not_ready_suffix
        try:
            open(temp_file, "wb").write(content)
        except IOError as e:
            self.logger.error('Error occured writing to file: {0}'.format(e))
            return self.Response('Failed to save file.',
                                 status=constants.HTTP_ERROR)
        del content


        metadata = _extract_exif_metadata(temp_file)
        result = {}
        if metadata.has_key('lat'):
            result['lat'] = metadata['lat']
        if metadata.has_key('lon'):
            result['lon'] = metadata['lon']

        key = datastore_client.key(self._datastore_kind, name)
        entity = datastore_client.get(key)
        if entity is not None:
            if 'user' in entity:
                if entity['user'] == datastore_client.key(self._user_datastore_kind, userid_hash):
                    entity['upload_session_id'] = upload_session_id
                    datastore_client.put(entity)
            else:
                self.logger.error('Duplicate detected but incomplete datastore record')
            try:
                os.remove(temp_file)
            except OSError as e:
                self.logger.error('Unable to remove file: {0}'.format(e))
            result['warning'] = 'Duplicate file upload.'
            return flask.jsonify(**result)
        entity = self._create_datastore_entry(
            datastore_client, name, original_filename, user=userid_hash,
            upload_session_id=upload_session_id, image_bucket=image_bucket,
            cc0_agree=cc0_agree, public_agree=public_agree)
        entity.update(metadata)
        if not entity:
            self.logger.error('Unable to create datastore entry for %s' % name)
            try:
                os.remove(temp_file)
            except OSError as e:
                self.logger.error('Unable to remove file: {0}'.format(e))
            return self.Response('Failed to save file.',
                                 status=constants.HTTP_ERROR)
        try:
            datastore_client.put(entity)
        except Exception as e:
            self.logger.error('Unable to create datastore entry for %s: %s' % (name, str(e)))
            try:
                os.remove(temp_file)
            except OSError as e:
                self.logger.error('Unable to remove file: {0}'.format(e))
            return self.Response('Failed to save file.',
                                 status=constants.HTTP_ERROR)

        try:
            os.rename(temp_file, local_file)
        except Exception as e:
            self.logger.error('Error occured rename file: {0}'.format(e))
            try:
                os.remove(temp_file)
            except OSError as e:
                self.logger.error('Unable to remove file: {0}'.format(e))
            return self.Response('Failed to save file.',
                                 status=constants.HTTP_ERROR)


        return flask.jsonify(**result)

    def _create_datastore_entry(self, datastore_client, filename, original_filename, user=None,
                                upload_session_id=None, image_bucket=None, cc0_agree=False, public_agree=False):
        """
        Creates and returns a datastore entity for a file with name filename
        uploaded by user user.
        Filename should be the new name we have generated that is <uuid>.<ext>.
        Raises FailedToSaveToDatastoreError if unsuccessful.
        """
        # Create datastore entity
        key = datastore_client.key(self._datastore_kind, filename)
        entity = self.datastore.Entity(key=key,
                                       exclude_from_indexes = ["exif_json"])

        # Set datastore entity data
        entity['user'] = datastore_client.key(self._user_datastore_kind, user)
        entity['upload_session_id'] = upload_session_id
        entity['confirmed_by_user'] = False
        entity['original_filename'] = original_filename
        entity['in_gcs'] = False
        entity['processed'] = False
        entity['uploaded_date'] = self.datetime.now()
        entity['image_bucket'] = image_bucket
        entity['cc0_agree'] = cc0_agree;
        entity['public_agree'] = public_agree

        if not ds.validate_data(entity, True, ds.DATASTORE_PHOTO):
            self.logger.error('Invalid entity: {0}'.format(entity))
            return None
        return entity

    def _check_role_in_roles(self, user_roles, allowed_roles):
        valid_role = False
        for role in user_roles:
            if role in allowed_roles:
                valid_role = True
                break
        return valid_role
