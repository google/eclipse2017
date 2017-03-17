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
import logging
from multiprocessing import Pool
import os

from gcloud import datastore, storage
from gcloud.exceptions import GCloudError
from gcloud.streaming.exceptions import Error as GCloudStreamingError

from common import config
from common import constants
from common import datastore_schema as ds
from common.eclipse2017_exceptions import CouldNotObtainCredentialsError
import common.service_account as sa
from common import util


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

    pool = Pool(min(len(fpaths), constants.UPLOAD_DAEMON_MAX_PROCESSES))
    results = pool.map(_upload_single, fpaths)
    pool.terminate()

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
        except GCloudError as e:
            error_msg = str(e)
            error = True

    if not error:
        # Add new entities as necessary
        if len(entities) != len(fpaths):
            entities = _insert_missing_entities(entities, fpaths)

        if success is False:
            new_data = {'gcs_upload_failed': True}
        else:
            new_data = {'in_gcs': True}

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
        except GCloudError as e:
            error_msg = str(e)
            error = True

    if error:
        msg = 'Failed to record {0} upload statuses in datastore: {1}'
        logging.error(msg.format(len(fpaths), error_msg))

    return fpaths if error else list()


def _upload_single(fpath):
    """
    Uploads single file to GCS. Returns a tuple containing
    (upload_success, fpath).
    """
    success = True

    try:
        client = _get_client('storage')
    except CouldNotObtainCredentialsError as e:
        logging.error('Could not obtain GCS credentials: {0}'.format(e))
        return False, fpath

    bucket = client.bucket(config.GCS_BUCKET)
    blob = storage.Blob(os.path.basename(fpath), bucket)

    try:
        blob.upload_from_filename(fpath)
        msg = 'Successfully uploaded {0} to GCS'
        logging.info(msg.format(fpath))

    except (GCloudError, GCloudStreamingError) as e:
        msg = '{0} failed to upload to GCS: {1}'
        logging.error(msg.format(fpath, e))
        success = False

    return success, fpath
