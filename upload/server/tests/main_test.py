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

from common import constants
from common import datastore_schema as ds

from upload_server_test_base import UploadServerTestBase

from app.backend.upload_server import UploadServer


class MainTests(UploadServerTestBase):
    """
    Tests for upload server main file.
    """
    @classmethod
    def setUpClass(cls):
        super(MainTests, cls).setUpClass()
        cls.original_readiness_file = constants.UPLOAD_SERVER_READINESS_FILE
        # Temp override
        constants.UPLOAD_SERVER_READINESS_FILE = cls.readiness_file
        from app import main
        cls.main = main

    @classmethod
    def tearDownClass(cls):
        super(MainTests, cls).tearDownClass()
        # Clean up
        constants.UPLOAD_SERVER_READINESS_FILE = cls.original_readiness_file

    def test_environ_setup(self):
        self.assertIn('common/service_account.json',
                      os.environ['GOOGLE_APPLICATION_CREDENTIALS'])

    def test_upload_server_config(self):
        self.assertEqual(self.main.upload_server._file_not_ready_suffix,
                         constants.FILE_NOT_READY_SUFFIX)
        self.assertEqual(self.main.upload_server._dir, constants.UPLOAD_DIR)
        self.assertEqual(self.main.upload_server._datastore_kind,
                         ds.DATASTORE_PHOTO)
        self.assertEqual(self.main.upload_server._retrys, constants.RETRYS)
        # self.assertEqual(self.main.upload_server._readiness_file,
        #                  constants.UPLOAD_SERVER_READINESS_FILE)

    def test_wsgi_app_wrapper_config(self):
        self.assertEqual(self.main.app.app.name, 'nop')
        self.assertEqual(len(self.main.app.mounts), 1)
        self.assertEqual(self.main.app.mounts[constants.UPLOAD_SERVICE_URL_PREFIX],
                         self.main.upload_server)
