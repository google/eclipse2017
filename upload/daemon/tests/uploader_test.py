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

import os
import random

from mock import call, Mock
import unittest2

from google.cloud.datastore.entity import Entity as GCDEntity
from google.cloud.exceptions import GCloudError
from google.cloud.streaming.exceptions import Error as GCloudStreamingError

from common import config
from common import constants
from common import datastore_schema as ds
from common.eclipse2017_exceptions import CouldNotObtainCredentialsError
from common import util

from app import uploader

from common_tests.stub import KeyStub, Stub


class UploaderTests(unittest2.TestCase):
    """
    Tests for the Uploader class.
    """
    directory = '/tmp/eclipse_upload_daemon_temp_dir'
    state = dict()

    @classmethod
    def setUpClass(cls):
        os.mkdir(cls.directory)

        cls.state['storage'] = uploader.storage
        cls.state['datastore'] = uploader.datastore
        cls.state['datetime'] = uploader.datetime
        cls.state['Pool'] = uploader.Pool
        cls.state['sa.get_credentials'] = uploader.sa.get_credentials

    @classmethod
    def tearDownClass(cls):
        os.rmdir(cls.directory)

        uploader.storage = cls.state['storage']
        uploader.datastore = cls.state['datastore']
        uploader.datetime = cls.state['datetime']
        uploader.Pool = cls.state['Pool']
        uploader.sa.get_credentials = cls.state['sa.get_credentials']

    def setUp(self):
        self.file_not_ready_suffix = '.notready'
        self._temp_files = list()

        uploader.storage = Mock()
        uploader.datastore = Mock()
        uploader.datetime = Mock()
        uploader.Pool = Mock()
        uploader.sa.get_credentials = Mock()

    def tearDown(self):
        for fpath in self._temp_files:
            os.remove(fpath)
        self._temp_files = list()

    def test_heal_files_failed_to_upload(self):
        temp = uploader._record_status_in_datastore
        uploader._record_status_in_datastore = Mock()

        fnames = self._get_file_names(5)

        errors = uploader.UploadErrors()
        errors.failed_to_upload = fnames

        pool = Mock()
        # Don't care about the return value here, just that it is iterable
        # so that uploader.upload doesn't complain
        pool.map = Mock(return_value=[])
        uploader.Pool = Mock(return_value=pool)

        # Call under test
        uploader.heal(errors)

        # Ensure upload was called correctly
        pool.map.assert_called_with(uploader._upload_single, fnames)

        # Clean up
        uploader._record_status_in_datastore = temp

    def test_heal_files_failed_to_delete(self):
        num_files = 5
        self._write_files(num_files, num_not_ready=0)

        errors = uploader.UploadErrors()
        errors.failed_to_delete = self._temp_files

        self.assertEqual(len(os.listdir(self.directory)), num_files)

        # Call under test
        uploader.heal(errors)

        self.assertEqual(len(os.listdir(self.directory)), 0)

        self._temp_files = list()

    def test_heal_files_failed_to_record_success_in_ds(self):
        temp = uploader._record_status_in_datastore
        uploader._record_status_in_datastore = Mock()

        fnames = self._get_file_names(5)

        for success in (True, False):
            errors = uploader.UploadErrors()
            if success:
                errors.datastore_success = fnames
            else:
                errors.datastore_failure = fnames

            # Call under test
            uploader.heal(errors)
            uploader._record_status_in_datastore.assert_called_with(
                fnames, success=success)

        # Clean up
        uploader._record_status_in_datastore = temp

    def test_scan(self):

        # Call under test
        fpaths = uploader.scan(self.directory, file_ready=self._file_ready)
        self.assertEqual(len(fpaths), 0)

        num_files = 10
        num_not_ready = 2
        self._write_files(num_files, num_not_ready)

        # Call under test
        fpaths = uploader.scan(self.directory, file_ready=self._file_ready)
        self.assertEqual(len(fpaths), num_files - num_not_ready)

    def test_upload_no_files(self):
        # Call under test
        ret_val = uploader.upload([])

        self.assertEqual(ret_val, uploader.UploadErrors())

        # First thing called by _upload_single is _get_client
        # Assert that no clients were created
        uploader.datastore.Client.assert_not_called()

    def test_upload_correct_threads_created(self):
        # Mock this out for our test
        temp = uploader._record_status_in_datastore
        uploader._record_status_in_datastore = Mock()

        for adder in [-2, 2]:
            num_files = constants.UPLOAD_DAEMON_MAX_PROCESSES + adder
            exp_threads = min(num_files, constants.UPLOAD_DAEMON_MAX_PROCESSES)

            self._write_files(num_files, num_not_ready=0)
            fpaths = self._temp_files
            results = [(True, fpath) for fpath in fpaths]

            pool = Mock()
            pool.map = Mock(return_value=results)
            uploader.Pool = Mock(return_value=pool)

            # Call under test
            ret_val = uploader.upload(fpaths)

            uploader.Pool.assert_called_with(exp_threads)
            pool.map.assert_called_with(uploader._upload_single,
                                        fpaths)

            # These were deleted by the call to upload
            self._temp_files = list()

        uploader._record_status_in_datastore = temp

    def test_upload_correct_calls_to_record_status_in_ds_made(self):
        # We will mock this out for our test
        temp = uploader._record_status_in_datastore
        uploader._record_status_in_datastore = Mock()

        # Create files to upload
        num_files = constants.UPLOAD_DAEMON_MAX_PROCESSES
        self._write_files(num_files, num_not_ready=0)
        fpaths = self._temp_files

        successful_uploads, failed_uploads = list(), list()
        for i in range(len(fpaths)):
            if 1 % 2 == 0:
                successful_uploads.append(fpaths[i])
            else:
                failed_uploads.append(fpaths[i])

        results = [(True, p) for p in successful_uploads]
        results.extend([(False, p) for p in failed_uploads])

        pool = Mock()
        pool.map = Mock(return_value=results)
        uploader.Pool = Mock(return_value=pool)

        # Call under test
        ret_val = uploader.upload(fpaths)

        call1 = call(successful_uploads, success=True)
        call2 = call(failed_uploads, success=False)
        calls = [call1, call2]
        uploader._record_status_in_datastore.assert_has_calls(calls)

        # These were deleted by the call to upload
        self._temp_files = list()

        uploader._record_status_in_datastore = temp

    def test_upload_record_status_in_ds_ret_vals_saved(self):
        # We will mock this out for our test
        temp = uploader._record_status_in_datastore
        num_files = constants.UPLOAD_DAEMON_MAX_PROCESSES

        for ds_failure in (True, False):

            def _record_in_datastore_mock(fpaths, success):
                return fpaths if ds_failure else []

            uploader._record_status_in_datastore = _record_in_datastore_mock

            # Create files to upload
            self._write_files(num_files, num_not_ready=0)
            fpaths = self._temp_files

            # Make some files upload successfully while others fail
            successful_uploads, failed_uploads = list(), list()
            for i in range(len(fpaths)):
                if 1 % 2 == 0:
                    successful_uploads.append(fpaths[i])
                else:
                    failed_uploads.append(fpaths[i])

            results = [(True, p) for p in successful_uploads]
            results.extend([(False, p) for p in failed_uploads])

            pool = Mock()
            pool.map = Mock(return_value=results)
            uploader.Pool = Mock(return_value=pool)

            # Call under test
            ret_val = uploader.upload(fpaths)

            if ds_failure:
                record_success_in_ds_failures = successful_uploads
                record_failure_in_ds_failures = failed_uploads
            else:
                record_success_in_ds_failures = []
                record_failure_in_ds_failures = []

            self.assertEqual(ret_val.datastore_success,
                             record_success_in_ds_failures)
            self.assertEqual(ret_val.datastore_failure,
                             record_failure_in_ds_failures)

            for fpath in failed_uploads:
                os.remove(fpath)
            self._temp_files = list()

        uploader._record_status_in_datastore = temp

    def test_upload_files_deleted(self):
        # We will mock this out for our test
        temp = uploader._record_status_in_datastore
        uploader._record_status_in_datastore = Mock()

        for success in (True, False):
            # Create files to upload
            num_files = constants.UPLOAD_DAEMON_MAX_PROCESSES
            self._write_files(num_files, num_not_ready=0)
            fpaths = self._temp_files

            results = [(True, p) for p in fpaths]

            pool = Mock()
            pool.map = Mock(return_value=results)
            uploader.Pool = Mock(return_value=pool)

            exp_len = 0

            # Force a failure
            if not success:
                temp_retry_func = uploader.util.retry_func
                uploader.util.retry_func = Mock(side_effect=RuntimeError)
                exp_len = len(fpaths)

            # Call under test
            ret_val = uploader.upload(fpaths)

            self.assertEqual(len(ret_val.failed_to_delete), exp_len)
            self.assertEqual(len(os.listdir(self.directory)), exp_len)

            # Clean up
            if not success:
                for fpath in fpaths:
                    os.remove(fpath)
                # Reset the retry function
                uploader.util.retry_func = temp_retry_func

            # These were deleted by the call to upload or above code block
            self._temp_files = list()

        uploader._record_status_in_datastore = temp

    def test_delete_all_files(self):
        num_files = 10
        self._write_files(num_files, num_not_ready=0)

        self.assertEqual(num_files, len(os.listdir(self.directory)))

        # Call under test
        uploader._delete_all_files(self._temp_files)
        self.assertEqual(0, len(os.listdir(self.directory)))

        # We have deleted them all
        self._temp_files = list()

    def test_get_client_could_not_obtain_credentials(self):
        uploader.sa.get_credentials = Mock(
            side_effect=CouldNotObtainCredentialsError)

        with self.assertRaises(CouldNotObtainCredentialsError):
            # Call under test
            ret_val = uploader._get_client(client_type='datastore')

        uploader.datastore.Client.assert_not_called()

    # def test_get_client_for_datastore(self):
    #     credentials = 'secret'
    #     uploader.sa.get_credentials = Mock(return_value=credentials)
    #     uploader.datastore.Client = Stub('datastore.Client')

    #     # Call under test
    #     ret_val = uploader._get_client(client_type='datastore')

    #     self.assertEqual(
    #         ret_val, Stub('datastore.Client', config.PROJECT_ID, credentials))

    # def test_get_client_for_gcs(self):
    #     credentials = 'secret'
    #     uploader.sa.get_credentials = Mock(return_value=credentials)
    #     uploader.storage.client.Client = Stub('storage.client.Client')

    #     # Call under test
    #     ret_val = uploader._get_client(client_type='storage')

    #     self.assertEqual(ret_val, Stub('storage.client.Client',
    #                                    config.PROJECT_ID, credentials))

    def test_get_ds_key_for_file(self):
        fname = 'to.file'
        fpath = '/arbitrary/path/' + fname
        uploader.datastore.key.Key = Stub('datastore.key.Key')

        # Call under test
        ret_val = uploader._get_ds_key_for_file(fpath)

        exp_ret_val = Stub('datastore.key.Key', ds.DATASTORE_PHOTO,
                           fname, project=config.PROJECT_ID)
        self.assertEqual(ret_val, exp_ret_val)

    def test_insert_missing_entities(self):
        now = 'now'
        fnames = self._get_file_names(10)

        entities = list()
        # Create entities for half the files
        for i in range(len(fnames)):
            if i % 2 != 1:
                key = KeyStub(ds.DATASTORE_PHOTO, fnames[i])
                entities.append(GCDEntity(key=key))

        uploader.datetime.now = Mock(return_value=now)
        uploader.datastore.entity.Entity = GCDEntity
        uploader.datastore.key.Key = KeyStub

        # Insert missing entities should work with file paths or names
        prefixes = ('', '/some/arbitrary/path/')
        for prefix in prefixes:
            fpaths = [prefix + fname for fname in fnames]

            # Call under test
            ret_val = uploader._insert_missing_entities(entities, fpaths)

            self.assertEqual(len(ret_val), len(fnames))
            for fname in fnames:
                self.assertTrue(
                    util.in_list(ret_val, fname, key=lambda x: x.key.name))

            # All the new eitities (the second half of them) should have the
            # following
            for i in range(len(fnames) / 2, len(fnames)):
                self.assertNotIn('user', entities[i])
                self.assertEqual(entities[i]['uploaded_date'], now)

    def test_record_status_in_datastore_could_not_obtain_credentials(self):
        fnames = self._get_file_names(5)
        uploader.datastore.Client = Mock(
            side_effect=CouldNotObtainCredentialsError)

        # Call under test
        ret_val = uploader._record_status_in_datastore(fnames, success=True)
        self.assertEqual(ret_val, fnames)

    def test_record_status_in_datastore_error_getting_entities(self):
        fnames = self._get_file_names(5)
        gcloud_error = GCloudError('')
        # Must set the code since __str__ will be called on this instance.
        # There is no way to set the code through the __init__ method
        gcloud_error.code = 500

        client = Mock()
        client.get_multi = Mock(side_effect=gcloud_error)
        uploader.datastore.Client = Mock(return_value=client)
        uploader.datastore.key.Key = KeyStub

        # Call under test
        ret_val = uploader._record_status_in_datastore(fnames, success=True)

        keys = [KeyStub(ds.DATASTORE_PHOTO, f, project=config.PROJECT_ID)
                for f in fnames]

        self.assertEqual(ret_val, fnames)
        client.get_multi.assert_called_with(keys)
        client.put_multi.assert_not_called()

    def test_record_status_in_datastore_restricted_fields_in_fetched_entities(self):
        num_files = 5
        fnames = self._get_file_names(num_files)

        # user is a restricted field for datastore photo entities - see
        # common/constants.py
        entities = [{'user': 123456789} for _ in range(num_files)]

        client = Mock()
        client.get_multi = Mock(return_value=entities)
        uploader.datastore.Client = Mock(return_value=client)
        uploader.datastore.key.Key = KeyStub

        # Call under test
        ret_val = uploader._record_status_in_datastore(fnames, success=True)

        keys = [KeyStub(ds.DATASTORE_PHOTO, f, project=config.PROJECT_ID)
                for f in fnames]

        self.assertEqual(ret_val, list())
        client.get_multi.assert_called_with(keys)
        # Entities should have been put into datastore, despite having
        # restricted fields - this is because the validate data function
        # is only called on the new data.
        client.put_multi.assert_called_with(entities)

    def test_record_status_in_datastore_error_saving_to_datastore(self):
        num_files = 5
        fnames = self._get_file_names(num_files)
        gcloud_error = GCloudError('')
        # Must set the code since __str__ will be called on this instance.
        # There is no way to set the code through the __init__ method
        gcloud_error.code = 500
        entities = [dict() for _ in range(num_files)]

        client = Mock()
        client.get_multi = Mock(return_value=entities)
        client.put_multi = Mock(side_effect=gcloud_error)

        uploader.datastore.Client = Mock(return_value=client)
        uploader.datastore.key.Key = KeyStub

        # Call under test
        ret_val = uploader._record_status_in_datastore(fnames, success=True)

        keys = [KeyStub(ds.DATASTORE_PHOTO, f, project=config.PROJECT_ID)
                for f in fnames]

        self.assertEqual(ret_val, fnames)
        client.get_multi.assert_called_with(keys)
        client.put_multi.assert_called_with(entities)

        # Make sure the entities were updated correctly
        for e in entities:
            self.assertTrue(e['in_gcs'])

    def test_record_status_in_datastore_missing_entities_success(self):
        num_files = 5
        fnames = self._get_file_names(num_files)

        entities = list()
        for i in range(num_files / 2):
            key = KeyStub(ds.DATASTORE_PHOTO, fnames[i])
            entities.append(GCDEntity(key=key))

        client = Mock()
        client.get_multi = Mock(return_value=entities)

        uploader.datastore.entity.Entity = GCDEntity
        uploader.datastore.Client = Mock(return_value=client)
        uploader.datastore.key.Key = KeyStub

        # Call under test
        ret_val = uploader._record_status_in_datastore(fnames, success=True)

        keys = [KeyStub(ds.DATASTORE_PHOTO, f, project=config.PROJECT_ID)
                for f in fnames]

        self.assertEqual(ret_val, [])
        client.get_multi.assert_called_with(keys)
        client.put_multi.assert_called_with(entities)

        # Make sure the entities were updated correctly
        self.assertEqual(len(entities), len(fnames))
        for e in entities:
            self.assertTrue(e['in_gcs'])

    def test_record_status_in_datastore_success(self):
        num_files = 5
        fnames = self._get_file_names(num_files)

        entities = list()
        for i in range(num_files):
            key = KeyStub(ds.DATASTORE_PHOTO, fnames[i])
            entities.append(GCDEntity(key=key))

        client = Mock()
        client.get_multi = Mock(return_value=entities)

        uploader.datastore.Client = Mock(return_value=client)
        uploader.datastore.key.Key = KeyStub

        for success in (True, False):
            # Call under test
            ret_val = uploader._record_status_in_datastore(fnames,
                                                           success=success)

            keys = [KeyStub(ds.DATASTORE_PHOTO, f, project=config.PROJECT_ID)
                    for f in fnames]

            self.assertEqual(ret_val, [])
            client.get_multi.assert_called_with(keys)
            client.put_multi.assert_called_with(entities)

            # Make sure the entities were updated correctly
            for e in entities:
                field = 'in_gcs' if success else 'gcs_upload_failed'
                self.assertTrue(e[field])

    def test_upload_single_could_not_obtain_credentials_error(self):
        fpath = '/arbitrary/path/to.file'
        uploader.sa.get_credentials = Mock(
            side_effect=CouldNotObtainCredentialsError)

        # Call under test
        ret_success, ret_fpath = uploader._upload_single(fpath)

        self.assertFalse(ret_success)
        self.assertEqual(ret_fpath, fpath)

        uploader.storage.client.Client.assert_not_called()
        uploader.storage.Blob.assert_not_called()

    def test_upload_single_gcs_upload_error(self):
        gcloud_error = GCloudError('')
        gcloud_error.code = 500
        streaming_error = GCloudStreamingError()

        for error in (gcloud_error, streaming_error):

            fpath = '/arbitrary/path/to.file'
            bucket = Mock()
            blob = Mock()
            client = Mock()

            blob.upload_from_filename = Mock(side_effect=error)
            client.bucket = Mock(return_value=bucket)

            uploader.storage.Blob = Mock(return_value=blob)
            uploader.storage.client.Client = Mock(return_value=client)

            # Call under test
            ret_success, ret_fpath = uploader._upload_single(fpath)

            self.assertFalse(ret_success)
            self.assertEqual(ret_fpath, fpath)

    def test_upload_single_success(self):
        fname = 'to.file'
        fpath = '/arbitrary/path/' + fname
        bucket = Mock()
        blob = Mock()
        client = Mock()

        client.bucket = Mock(return_value=bucket)
        uploader.storage.Blob = Mock(return_value=blob)
        uploader.storage.client.Client = Mock(return_value=client)

        # Call under test
        ret_success, ret_fpath = uploader._upload_single(fpath)

        self.assertTrue(ret_success)
        self.assertEqual(ret_fpath, fpath)

        blob.upload_from_filename.assert_called_with(fpath)
        client.bucket.assert_called_with(config.GCS_BUCKET)
        uploader.storage.Blob.assert_called_with(fname, bucket)

        # Called by sa.get_credentials
        uploader.storage.client.Client.assert_called()

    def _file_ready(self, fpath):
        """
        Function passed to uploader.scan to return whether a given file is ready
        to be uploaded or not.
        """
        return not fpath.endswith(self.file_not_ready_suffix)

    @staticmethod
    def _get_file_names(num_files):
        return ['file' + str(i) for i in range(num_files)]

    def _get_some_data(self, num_bytes=1024):
        """
        Return a random string with num_bytes characters.
        """
        return ''.join([chr(ord('a') + int(25 * random.random()))
                        for _ in range(num_bytes)])

    def _write_files(self, num_files, num_not_ready):

        if num_not_ready > num_files:
            raise ValueError('num_not_ready > num_files')

        files = self._get_file_names(num_files)

        for i in range(num_files):
            if i < num_not_ready:
                files[i] += self.file_not_ready_suffix

            fpath = os.path.join(self.directory, files[i])

            with open(fpath, 'w') as f:
                f.write(self._get_some_data())

            self._temp_files.append(fpath)
