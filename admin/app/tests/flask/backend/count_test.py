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

from app.backend.eclipse2017_admin_app import Eclipse2017AdminApp
from google.cloud import datastore

from common import config
from common import secret_keys as sk
from common import roles
from common import users

from common import test_common
from common import util

class CountTests(unittest2.TestCase):
    """
    Tests for Count class.
    """
    def __init__(self, *args, **kwargs):
        super(CountTests, self).__init__(*args, **kwargs)
        self.USER = '1'
        self.USER2 = '2'

        self.USER_HASH = unicode(users.get_userid_hash(self.USER))
        self.USER2_HASH = users.get_userid_hash(self.USER2)

        # Fake user idtoken verifier
        class id_token:
            def __init__(self, user):
                self.user = user
            def verify_token(self, token, _):
                return { 'iss': 'accounts.google.com',
                         'sub': self.user}

        self.id_token = id_token(self.USER)
        self.id_token2 = id_token(self.USER2)
        util.id_token = self.id_token

        self.HEADERS={'Content-type': 'application/json',
                      'X-IDTOKEN': self.USER}

    def setUp(self):
        self.app = Eclipse2017AdminApp(config.PROJECT_ID, sk.FLASK_SESSION_ENC_KEY,
                                       sk.GOOGLE_OAUTH2_CLIENT_ID,
                                       sk.GOOGLE_OAUTH2_CLIENT_SECRET)

        self.test_client = self.app.test_client()
        if 'prod' in config.PROJECT_ID:
            raise RuntimeError('Cowardly refusing to delete prod datastore')
        self.datastore_client = datastore.Client(config.PROJECT_ID)
        test_common._clear_data(self.datastore_client)

    def _get_count_root(self, headers=None, expected_status=200):
        if headers is None: headers = self.HEADERS
        ret_val = self.test_client.get('/services/admin/users/count/',
                                       headers=headers)
        if ret_val.status_code != expected_status:
            print "Error: ", ret_val.data
        self.assertEqual(ret_val.status_code, expected_status)
        return ret_val

    def _setup_user(self, userid_hash):
        json = {"email": "test@example.com"}

        key = self.datastore_client.key("User", userid_hash)
        entity = datastore.Entity(key=key)
        util._update_entity(json, {'email'}, entity)
        self.datastore_client.put(entity)

    def test_get_count(self):
        self._setup_user(self.USER_HASH)
        roles.create_user_role(self.datastore_client, self.USER_HASH, [u'admin'])
        self._get_count_root(expected_status=200)

    def test_get_count_not_admin(self):
        self._setup_user(self.USER_HASH)
        roles.create_user_role(self.datastore_client, self.USER_HASH, [u'user'])
        self._get_count_root(expected_status=403)

    def test_get_count_missing_auth(self):
        self._get_count_root(headers={}, expected_status=405)
