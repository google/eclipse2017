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

import unittest2

from common import datastore_schema as ds


class ValidateDataTests(unittest2.TestCase):

    def setUp(self):
        # Note: this contains the restricted field 'deleted'
        self.valid_user_data = {
            'geolat': 100.0,
            'geolng': 87.23,
            'deleted': True
        }
        self.user_kind = ds.DATASTORE_USER

    def test_validate_data_entity_not_allowed(self):
        kind = 'evilEntity'
        # Call under test
        ret_val = ds.validate_data(self.valid_user_data, True, kind)
        self.assertFalse(ret_val)

    def test_validate_data_field_not_allowed_fail(self):
        data = {'bad': 'data', 'evil': 'monsters'}
        data.update(self.valid_user_data)
        allow_restricted_fields = True

        # Call under test
        ret_val = ds.validate_data(data, allow_restricted_fields, self.user_kind)
        self.assertFalse(ret_val)

    def test_validate_data_field_restricted_fail(self):
        allow_restricted_fields = False

        # Call under test
        ret_val = ds.validate_data(self.valid_user_data, allow_restricted_fields,
                                   self.user_kind)
        self.assertFalse(ret_val)

    def test_validate_data_pass(self):
        allow_restricted_fields = True

        # Call under test
        ret_val = ds.validate_data(self.valid_user_data, allow_restricted_fields,
                                   self.user_kind)
        self.assertTrue(ret_val)
