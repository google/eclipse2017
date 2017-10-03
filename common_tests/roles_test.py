#
# Copyright 2017 Google Inc.
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

import json
import unittest2

from common import roles

from google.cloud import datastore
from common import config
from common import test_common
from common.eclipse2017_exceptions import MissingUserError
from common import util
from common import users


class RolesTest(unittest2.TestCase):
    """
    Tests for Profile class.
    """

    def __init__(self, *args, **kwargs):
        super(RolesTest, self).__init__(*args, **kwargs)
        self.USER = '1'
        self.USER_HASH = users.get_userid_hash(self.USER)

    def setUp(self):
        if 'prod' in config.PROJECT_ID:
            raise RuntimeError('Cowardly refusing to delete prod datastore')
        self.datastore_client = datastore.Client(config.PROJECT_ID)
        test_common._clear_data(self.datastore_client)

    def test_get_all_user_roles_nousers(self):
        get_roles = roles.get_all_user_roles(self.datastore_client)
        self.assertEqual(get_roles, {})

    def test_get_all_user_roles(self):
        result = roles.create_user_role(self.datastore_client, self.USER_HASH)
        self.assertTrue(result)
        get_roles = roles.get_all_user_roles(self.datastore_client)
        self.assertEqual(get_roles, {self.USER_HASH:['user']})

    def test_get_user_role_nouser(self):
        with self.assertRaises(MissingUserError):
          roles.get_user_role(self.datastore_client, self.USER_HASH)

    def test_get_user_role(self):
        result = roles.create_user_role(self.datastore_client, self.USER_HASH)
        self.assertTrue(result)
        get_roles = roles.get_user_role(self.datastore_client, self.USER_HASH)
        self.assertEqual(get_roles, ['user'])

    def test_create_user_role_exists(self):
        result = roles.create_user_role(self.datastore_client, self.USER_HASH)
        self.assertTrue(result)
        result = roles.create_user_role(self.datastore_client, self.USER_HASH)
        self.assertFalse(result)

    def test_update_user_role_nouser(self):
        result = roles.update_user_role(self.datastore_client, self.USER_HASH, {})
        self.assertFalse(result)

    def test_update_user_role(self):
        result = roles.create_user_role(self.datastore_client, self.USER_HASH)
        self.assertTrue(result)
        result = roles.update_user_role(self.datastore_client, self.USER_HASH, ['admin'])
        self.assertTrue(result)
        get_roles = roles.get_user_role(self.datastore_client, self.USER_HASH)
        self.assertEqual(get_roles, ['admin'])

    def test_delete_user_role_nouser(self):
        result = roles.delete_user_role(self.datastore_client, self.USER_HASH)
        self.assertFalse(result)

    def test_delete_user_role(self):
        result = roles.create_user_role(self.datastore_client, self.USER_HASH)
        self.assertTrue(result)
        result = roles.delete_user_role(self.datastore_client, self.USER_HASH)
        self.assertTrue(result)
        get_roles = roles.get_all_user_roles(self.datastore_client)
        self.assertEqual(get_roles, {})
