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

import sys
import traceback
from datetime import datetime
import logging
from multiprocessing import Pool
import os
import io
import json
from functools import partial
import shutil

from google.cloud import datastore, storage, vision

from common.geometry import getRescaledDimensions
from common import config
from common import constants
from common import datastore_schema as ds
from common.eclipse2017_exceptions import CouldNotObtainCredentialsError
import common.service_account as sa
from common import util
from PIL import Image
from common.geometry import ratio_to_decimal
from common.exif import _extract_exif_metadata, _extract_image_metadata
import exifread
from rawkit.raw import Raw
from rawkit.options import WhiteBalance

class UploadErrors(object):

    def __init__(self):
        # List of file paths that failed to upload to Cloud Storage
        self.failed_to_upload = list()

        # List of files that failed to delete
        self.failed_to_delete = list()

        # List of files that uploaded successfully however this failed to be
        # captured in datastore
        self.datastore_success = list()

        # List of files that failed to upload and this failed to be
        # captured in datastore
        self.datastore_failure = list()


    def __eq__(self, other):
        eq = True
        eq &= self.failed_to_upload == other.failed_to_upload
        eq &= self.failed_to_delete == other.failed_to_delete
        eq &= self.datastore_success == other.datastore_success
        eq &= self.datastore_failure == other.datastore_failure
        return eq


def heal(errors):
    """
    Attempts to resolve any upload errors that may have occured. `errors` is an
    UploadErrors object.
    """
    logging.info('Attempting to heal any upload errors that occured...')

    if len(errors.failed_to_upload) > 0:
        upload(errors.failed_to_upload)

    if len(errors.failed_to_delete) > 0:
        _delete_all_files(errors.failed_to_delete)

    if len(errors.datastore_success) > 0:
        _record_status_in_datastore(errors.datastore_success, success=True)

    if len(errors.datastore_failure) > 0:
        _record_status_in_datastore(errors.datastore_failure, success=False)


def scan(directory, file_ready):
    """
    Scans directory for files. A list of all ready files is returned. A given
    file is considered ready if file_ready(f) returns true for
    that file, where f is the files name.
    """
    # Get files to upload
    fpaths = [os.path.join(directory, f) for f in os.listdir(directory)
              if file_ready(f)]

    if len(fpaths) > 0:
        msg = 'Scanned {0}. Found {1} files to upload'
        logging.info(msg.format(directory, len(fpaths)))

    return fpaths


def upload(fpaths):
    """
    Uploads files pointed to by paths in `fpaths` list to GCS using up to
    `constants.UPLOAD_DAEMON_MAX_PROCESSES` processes. Files that are
    successfully uploaded are deleted from local disk. Each file's upload status
    is recorded in datastore.

    Errors are returned in an `UploadErrors` instace that has lists of files
    that:
        - failed to upload to GCS
        - uploaded to GCS but failed to be delete from the local file system
        - uploaded to GCS but failed to have this recorded in datastore
        - failed to upload to GCS and this failed to be recorded in datastore
    """
    errors = UploadErrors()

    if not len(fpaths) > 0:
        return errors

    logging.info('Uploading {0} files'.format(len(fpaths)))

    results = []
    for fpath in fpaths:
        result = _upload_single(fpath)
        results.append(result)

    logging.info('Uploaded {0} files'.format(len(fpaths)))

    # Seperate files that uploaded successfully from those that didn't
    uploaded_files = [r[1] for r in results if r[0] is True]
    errors.failed_to_upload = [r[1] for r in results if r[0] is False]

    # Delete files that were successfully uploaded, keep track of any that
    # fail to delete
    errors.failed_to_delete = _delete_all_files(uploaded_files)

    errors.datastore_success = _record_status_in_datastore(
        uploaded_files, success=True)

    errors.datastore_failure = _record_status_in_datastore(
        errors.failed_to_upload, success=False)

    return errors


def _delete_all_files(fpaths):
    """
    Deletes each file in fpaths. Returns list of file paths that failed to
    delete.
    """
    failed_to_delete = list()

    for p in fpaths:
        try:
            util.retry_func(os.remove, constants.RETRYS, (OSError, ), p)
        except RuntimeError:
            failed_to_delete.append(p)

    return failed_to_delete


def _get_client(client_type='storage'):
    """
    Returns gcloud client, (either for storage if `client_type` is 'storage',
    or for datastore if `client_type` is 'datastore'). Defaults to storage
    client, including when an invalid `client_type` is given.
    Raises `CouldNotObtainCredentialsError` if there is an error obtaining
    credentials.
    """
    # Raises CouldNotObtainCredentialsError
    credentials = sa.get_credentials()

    if client_type == 'datastore':
        client_class = datastore.Client
    else:
        client_class = storage.client.Client

    return client_class(project=config.PROJECT_ID, credentials=credentials)


def _get_ds_key_for_file(fpath):
    """
    Gets a datastore key for a file.
    """
    return datastore.key.Key(ds.DATASTORE_PHOTO, os.path.basename(fpath),
                             project=config.PROJECT_ID)


def _insert_missing_entities(entities, fpaths):
    """
    Creates datastore entities for all files in fpaths  that do not already have
    a corresponding entity in entities. Returns original entities list with
    any missing entities added to the end.
    """
    def cmp_key(entity):
        try:
            return entity.key.name
        except AttributeError:
            return ''

    for p in fpaths:
        if not util.in_list(entities, os.path.basename(p), key=cmp_key):
            key = _get_ds_key_for_file(p)
            entity = datastore.entity.Entity(key=key)
            entity['uploaded_date'] = datetime.now()
            entities.append(entity)

    return entities


def _record_status_in_datastore(fpaths, success):
    """
    Records GCS upload status in datastore for each file fpaths.
    `success` is a boolean corresponding to whether the files in fpaths were
    uploaded successfully to GCS or not. A list of files that failed to have
    their upload status updated are returned.
    """
    error_msg = ''
    error = False

    try:
        client = _get_client('datastore')
    except CouldNotObtainCredentialsError as e:
        error_msg = 'Could not obtain datastore credentials: {0}'.format(e)
        error = True

    if not error:
        keys = list()

        for p in fpaths:
            key = _get_ds_key_for_file(p)
            keys.append(key)

        try:
            entities = client.get_multi(keys)
        except Exception as e:
            error_msg = str(e)
            error = True

    if not error:
        # Add new entities as necessary
        if len(entities) != len(fpaths):
            entities = _insert_missing_entities(entities, fpaths)

        if success is False:
            new_data = {'gcs_upload_failed': True, 'in_gcs': False}
        else:
            new_data = {'in_gcs': True, 'gcs_upload_failed': False}

        # We only want to validate the new data, as there may be restricted
        # fields in the entities we pulled from datastore. All new data must
        # be validated as follows before adding it to the entities that will be
        # pushed to datastore.
        if not ds.validate_data(new_data, allow_restricted_fields=False,
                                kind=ds.DATASTORE_PHOTO):
            error_msg = 'Invalid data: {0}'.format(new_data)
            error = True

    if not error:
        # Update entities
        for i in range(len(entities)):
            entities[i].update(new_data)

        # Save to datastore
        try:
            client.put_multi(entities)
        except Exception as e:
            error_msg = str(e)
            error = True

    if error:
        msg = 'Failed to record {0} upload statuses in datastore: {1}'
        logging.error(msg.format(len(fpaths), error_msg))

    return fpaths if error else list()


def _check_adult_content(img):
    """
    Checks if img contains adult content.
    Returns True if img contains adult content.
    """
    first, second = getRescaledDimensions(img.width, img.height, 640, 480)
    try:
        resize = img.resize((first, second), Image.ANTIALIAS)
    except IOError:
        logging.error("Invalid image cannot be resized.")
        # Have to assume image is adult content
        return True
    out = io.BytesIO()
    resize.convert('RGB').save(out, format='JPEG')
    vision_client = vision.Client()
    vc_img = vision_client.image(content=out.getvalue())
    safe = vc_img.detect_safe_search()
    if safe.adult == vision.likelihood.Likelihood.LIKELY or safe.adult == vision.likelihood.Likelihood.POSSIBLE:
        logging.error("Detected likely adult content upload.")
        return True
    return False

def _upload_derived(derived_file, bucket):
    blob = storage.Blob(os.path.basename(derived_file), bucket)

    # Upload derived file
    try:
        blob.upload_from_filename(derived_file)
        msg = 'Successfully uploaded derived {0} to GCS'
        logging.info(msg.format(derived_file))

    except Exception as e:
        msg = 'Derived {0} failed to upload to GCS: {1}'
        logging.error(msg.format(derived_file, e))
        return False
    return True

def _upload_single(fpath):
    """
    Uploads single file to GCS. Returns a tuple containing
    (upload_success, fpath).
    """
    try:
        bucket_name = config.GCS_BUCKET
        success = True
        try:
            datastore_client = _get_client('datastore')
        except CouldNotObtainCredentialsError as e:
            error_msg = 'Could not obtain datastore credentials: {0}'.format(str(e))
            logging.error(error_msg)
            return False, fpath

        try:
            client = _get_client('storage')
        except CouldNotObtainCredentialsError as e:
            logging.error('Could not obtain GCS credentials: {0}'.format(str(e)))
            return False, fpath
        bucket = client.bucket(bucket_name)

        # Verify that filename already exists as key in database
        filename = os.path.basename(fpath)

        key = datastore_client.key('Photo', filename)
        entity = datastore_client.get(key)
        if entity is None:
            logging.error('Failed to find file: ' + filename)
            return False, fpath

        try:
            img = Image.open(fpath)
            format_ = img.format
            if format_  == 'TIFF':
                output_file = "/tmp/" + filename + ".jpg"
                img.save(output_file)
                _upload_derived(output_file, bucket)
                os.unlink(output_file)
        except IOError as e:
            try:
                with Raw(filename=fpath) as raw:
                    tiff_output_file = "/tmp/" + filename + ".tiff"
                    raw.save(filename=tiff_output_file)
            except Exception as e:
                logging.error("Failed to parse file with PIL or rawkit: %s (error: %s)" % (fpath, str(e)))
                # move the file out of the pending tree so it won't be processed next loop
                try:
                    shutil.move(fpath, "/tmp/%s" % os.path.basename(fpath))
                except IOError as e:
                    logging.error("Unable to move bad file out of the way: %s (error: %s)" % (fpath, str(e)))
                return False, fpath
            jpg_output_file = "/tmp/" + filename + ".jpg"
            img = Image.open(tiff_output_file)
            img.save(jpg_output_file)
            _upload_derived(jpg_output_file, bucket)
            os.unlink(tiff_output_file)
            os.unlink(jpg_output_file)
            format_ = 'raw'

        is_adult = _check_adult_content(img)
        if is_adult:
            entity.update({'is_adult_content': True})
            datastore_client.put(entity)
            os.unlink(fpath)
            return False, fpath
        else:
            entity.update({'is_adult_content': False})

        metadata = {}
        metadata['reviews'] = []
        metadata['num_reviews'] = 0
        entity.update(metadata)

        width = img.width
        height = img.height
        metadata = _extract_image_metadata(filename, format_, width, height, bucket_name)
        entity.update(metadata)
        if not ds.validate_data(entity, True, ds.DATASTORE_PHOTO):
            logging.error('Invalid entity: {0}'.format(entity))
            return False, fpath
        datastore_client.put(entity)

        blob = storage.Blob(os.path.basename(fpath), bucket)

        try:
            blob.upload_from_filename(fpath)
            msg = 'Successfully uploaded {0} to GCS'
            logging.debug(msg.format(fpath))

        except Exception as e:
            msg = '{0} failed to upload to GCS: {1}'
            logging.error(msg.format(fpath, e))
            success = False

        return success, fpath
    except Exception as e:
        logging.error("Failed to upload file: %s" % fpath)
        traceback.print_exc(limit=50)
        logging.error("Returning false")
        return False, fpath
