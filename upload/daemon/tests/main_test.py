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

import logging

from mock import Mock
import unittest2

from common import config, constants
from common.eclipse2017_exceptions import FailedToUploadToGCSError
from common import service_account as sa

from app import main


class AbortException(Exception):
    """
    Special exception class used to test the main function, since it is an
    infinite loop, we use this exception to break out of the loop and verify
    that it was the call to abort, and not some other call that raised an
    exception.
    """
    pass


class MainTests(unittest2.TestCase):
    """
    Tests for upload daemon main file.
    """
    state = dict()

    @classmethod
    def setUpClass(cls):
        cls.state['scan'] = main.uploader.scan
        cls.state['upload'] = main.uploader.upload
        cls.state['heal'] = main.uploader.heal

    @classmethod
    def tearDownClass(cls):
        main.uploader.scan = cls.state['scan']
        main.uploader.upload = cls.state['upload']
        main.uploader.heal = cls.state['heal']

    def setUp(self):
        self.files = ['file' + str(i) for i in range(10)]
        main.uploader.scan = Mock(return_value=self.files)
        main.uploader.upload = Mock()
        main.uploader.heal = Mock()

    def test_main_loops_forever(self):
        for num_safe_calls in (100, 10, 0, 200):
            side_effects = [None for _ in range(num_safe_calls)]
            side_effects.append(AbortException)

            main.uploader.heal = Mock(side_effect=side_effects)

            with self.assertRaises(AbortException):
                # Call under test
                main.main(sleep_time=0)

            self.assertEqual(len(main.uploader.heal.mock_calls),
                             num_safe_calls + 1)

    def test_main_heals_correctly(self):
        main.uploader.heal = Mock(side_effect=AbortException)

        with self.assertRaises(AbortException):
            # Call under test
            main.main(sleep_time=0)

        main.uploader.scan.assert_called_with(constants.UPLOAD_DIR,
                                              file_ready=main.file_ready)
        main.uploader.upload.assert_called_with(self.files)
        exp_errors = main.uploader.upload(self.files)
        main.uploader.heal.assert_called_with(exp_errors)

    def test_file_ready(self):
        fpath = '/arbitrary/file/path/to.thedatas'
        self.assertTrue(main.file_ready(fpath))

        fpath += constants.FILE_NOT_READY_SUFFIX
        self.assertFalse(main.file_ready(fpath))
