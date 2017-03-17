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
import json
import os
import threading
import time
from uuid import uuid4

import flask
from gcloud import datastore
from gcloud.exceptions import GCloudError
from werkzeug.exceptions import ClientDisconnected

from common import constants
from common import datastore_schema as ds
from common.eclipse2017_exceptions import FailedToRenameFileError
from common.eclipse2017_exceptions import FailedToSaveToDatastoreError
from common import util
from common import secret_keys as sk

from oauth2client import client, crypt


# TODO add authentication - this needs to use the same cookie as profile server


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

        # Fetch the user's identifier from the request, which
        # contains the oauth2 creds.
        try:
          token = flask.request.headers['X-IDTOKEN']
        except Exception as e:
            return flask.Response('Missing credential token header', 405)

        try:
            idinfo = client.verify_id_token(token, sk.GOOGLE_OAUTH2_CLIENT_ID)
            if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
                raise crypt.AppIdentityError("Wrong issuer.")
        except crypt.AppIdentityError:
                # Invalid token
            return flask.Response('Application identity error.', 405)
        user_id = idinfo['sub']
        hash_id = hashlib.sha256(user_id).hexdigest()

        content_type = self.request.content_type

        datastore_client = self.datastore.Client(self.config['PROJECT_ID'])
        batch = datastore_client.batch()

        for file_ in self.request.files.getlist('datafile'):
            # In case an error occured and the filename was not sent
            # filename = self.request.headers.get(constants.HTTP_FILENAME_HEADER) or ''
            filename = file_.filename
            ext = self.os.path.splitext(filename)[1].strip('.')
            name = '.'.join((str(uuid4()), ext))

            entity = self._create_datastore_entry(datastore_client, name, user=hash_id)

            if entity:
                batch.put(entity)

            # Local file system file paths
            local_file = self.os.path.join(self._dir, name)
            temp_file = local_file + self._file_not_ready_suffix

            try:
                self._write_data_to_file(temp_file, file_)

            except IOError as e:
                self.logger.error('Error occured writing to file: {0}'.format(e))
                return self.Response('Failed to save file.',
                                     status=constants.HTTP_ERROR)

            except ClientDisconnected:
                # This error will occur if Gunicorn/Flask fails to respond before
                # the load balancer times the request out. In this situation, the
                # load balancer responds to the client with a 502 error, however
                # this is not detected by Flask until it reads to the end of the
                # buffered request from nginx at which point this exception will be
                # thrown by the call to self.request.stream.read in
                # _write_data_to_file.
                try:
                    self.util.retry_func(self.os.remove, self._retrys,
                                         (OSError, ), temp_file)
                except RuntimeError:
                    pass
                self.logger.error('Upload failed. Client disconnected.')
                return self.Response(status=constants.HTTP_ERROR)

            try:
                self.util.retry_func(self.os.rename, self._retrys,
                                     (OSError, ), temp_file, local_file)
            except RuntimeError:
                return self.Response('Failed to save file.',
                                     status=constants.HTTP_ERROR)

        try:
            batch.commit()
        except FailedToSaveToDatastoreError as e:
            self.logger.error(str(e))
            # Continue on for now. The upload daemon will create a datastore
            # entity if it doesn't find one, it will just be missing the user
            # information.

        return self.Response(status=constants.HTTP_OK)

        def _create_datastore_entry(self, datastore_client, filename, user=None):
            """
            Creates and returns a datastore entity for a file with name filename
            uploaded by user user.
            Filename should be the new name we have generated that is <uuid>.<ext>.
            Raises FailedToSaveToDatastoreError if unsuccessful.
            """
        # Create datastore entity
        key = datastore_client.key(self._datastore_kind, filename)
        entity = self.datastore.Entity(key=key)

        # Set datastore entity data
        entity['user'] = datastore_client.key(self._user_datastore_kind, user)
        entity['in_gcs'] = False
        entity['processed'] = False
        entity['uploaded_date'] = self.datetime.now()

        if not ds.validate_data(entity, True, ds.DATASTORE_PHOTO):
            msg = 'Invalid entity: {0}'.format(entity)
            return None

        return entity

    def _write_data_to_file(self, filename, stream):
        """
        Read in upload data in chunks and save to temp file.
        """
        with open(filename, 'wb') as f:
            while True:
                chunk = stream.read(8 * constants.MB)
                if len(chunk) == 0:
                    break
                f.write(chunk)
