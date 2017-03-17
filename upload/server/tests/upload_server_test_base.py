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

import unittest2

from common import constants


class UploadServerTestBase(unittest2.TestCase):
    """
    Base class for upload server tests.
    """
    temp_dir = '/tmp/eclipse2017_upload_server_test_files'
    readiness_file = os.path.join(temp_dir, 'readiness_status')
    upload_dir = os.path.join(temp_dir, 'uploads')

    @classmethod
    def setUpClass(cls):
        """
        One time setup.
        """
        os.mkdir(cls.temp_dir)
        os.mkdir(cls.upload_dir)

        with open(cls.readiness_file, 'w') as f:
            f.write(constants.STATUS_READY)

    @classmethod
    def tearDownClass(cls):
        """
        One time tear down.
        """
        os.remove(cls.readiness_file)
        os.rmdir(cls.upload_dir)
        os.rmdir(cls.temp_dir)
