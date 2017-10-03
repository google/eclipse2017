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

import json
import unittest2

from app.backend.eclipse2017_app import Eclipse2017App
from google.cloud import datastore

from common import config
from common import secret_keys as sk
from common import users
from common import roles

from common import test_common
from common import util

class ProfileTests(unittest2.TestCase):
    """
    Tests for Profile class.
    """

    def __init__(self, *args, **kwargs):
        super(ProfileTests, self).__init__(*args, **kwargs)
        USER = '1'
        self.USER = USER
        USER2 = '2'
        self.USER2 = USER2
        self.USER_HASH = users.get_userid_hash(self.USER)
        self.USER2_HASH = users.get_userid_hash(self.USER2)

        # Fake user idtoken verifier
        class id_token:
            def __init__(self):
                pass
            def verify_token(self, token, _):
                return { 'iss': 'accounts.google.com',
                         'sub': USER}

        # Fake user idtoken verifier
        class id_token2:
            def __init__(self):
                pass
            def verify_token(self, token, _):
                return { 'iss': 'accounts.google.com',
                         'sub': USER2}

        self.id_token = id_token()
        self.id_token2 = id_token2()
        util.id_token = self.id_token

        self.HEADERS={'Content-type': 'application/json',
                      'X-IDTOKEN': USER}


    def setUp(self):
        self.app = Eclipse2017App(config.PROJECT_ID, sk.FLASK_SESSION_ENC_KEY,
                                  sk.GOOGLE_OAUTH2_CLIENT_ID,
                                  sk.GOOGLE_OAUTH2_CLIENT_SECRET)

        self.test_client = self.app.test_client()
        if 'prod' in config.PROJECT_ID:
            raise RuntimeError('Cowardly refusing to delete prod datastore')
        self.datastore_client = datastore.Client(config.PROJECT_ID)
        test_common._clear_data(self.datastore_client)

    def _get_root(self, headers=None, expected_status=200):
        if headers is None: headers = self.HEADERS
        ret_val = self.test_client.get('/services/user/profile/',
                                       headers=headers)
        if ret_val.status_code != expected_status:
            print "Error: ", ret_val.data
        self.assertEqual(ret_val.status_code, expected_status)
        return ret_val

    def _get_json(self, ret_val):
        h = ret_val.headers
        k = h.keys()
        self.assertIn('Content-Type', k)
        self.assertEqual(h.get('Content-Type'), 'application/json')
        j = json.loads(ret_val.data)
        return j

    def _get_user(self, user_id, headers=None, expected_status=200):
        if headers is None: headers = self.HEADERS
        ret_val = self.test_client.get('/services/user/profile/%s' % user_id,
                                       headers=headers)
        self.assertEqual(ret_val.status_code, expected_status)
        return ret_val

    def _put_user(self, user_id, data, headers=None, expected_status=200):
        if headers is None: headers = self.HEADERS
        ret_val = self.test_client.put('/services/user/profile/%s' % user_id,
                                       data=json.dumps(data), headers=headers)
        self.assertEqual(ret_val.status_code, expected_status)
        return ret_val

    def _update_user(self,user_id, update, headers=None, expected_status=200):
        if headers is None: headers = self.HEADERS
        ret_val = self.test_client.open('/services/user/profile/%s' % user_id,
                                        method = 'UPDATE',
                                        data=json.dumps(update),
                                        headers=headers)
        self.assertEqual(ret_val.status_code, expected_status, ret_val.data)
        return ret_val

    def _delete_user(self, user_id, headers=None, expected_status=200):
        if headers is None: headers = self.HEADERS
        ret_val = self.test_client.delete('/services/user/profile/%s' % user_id,
                                          headers=headers)

    def test_get_root(self):
        self._get_root(headers=None, expected_status=200)

    def test_get_user_missing(self):
        self._get_user(self.USER_HASH, expected_status=404)

    def test_get_user_missing_auth(self):
        self._get_user(self.USER_HASH, headers={}, expected_status=405)

    def test_get_user_wronguser(self):
        test_common._set_user_roles(roles, self.datastore_client, self.USER2_HASH, ['user'])
        # We'd prefer to do this with headers, but the fake id token verifier
        # gets in the way.
        util.id_token = self.id_token2
        try:
            # Other user cannot access user's profile
            self._get_user(self.USER_HASH, expected_status=403)
        finally:
            # Have to always clean up the monkey patch.
            util.id_token = self.id_token

    def test_put_user(self):
        data = {"email": "test@example.com"}
        ret_val = self._put_user(self.USER_HASH, data=data)
        ret_val = self._get_user(self.USER_HASH)
        j = self._get_json(ret_val)
        data['roles'] = ['user']
        self.assertEqual(j, data)

    def test_put_user_missing_auth(self):
        data = {"email": "test@example.com"}
        self._put_user(self.USER_HASH, data=data, headers={}, expected_status=405)

    def test_put_user_unexpected_field(self):
        data = {"email": "test@example.com", "bad_field": "1"}
        self._put_user(self.USER_HASH, data, expected_status=400)

    def test_update_user(self):
        data = {"email": "test@example.com"}
        self._put_user(self.USER_HASH, data)
        update = {"email": "test@example.com", "name": "example"}
        self._update_user(self.USER_HASH, update)
        ret_val = self._get_user(self.USER_HASH)
        j = self._get_json(ret_val)
        update['roles'] = ['user']
        self.assertEqual(j, update)

    def test_update_user_missing_auth(self):
        update = {"email": "test@example.com", "name": "example"}
        self._update_user(self.USER_HASH, update, headers={}, expected_status=405)

    def test_update_user_missing_email(self):
        data = {"email": "test@example.com"}
        self._put_user(self.USER_HASH, data)
        update = {"name": "example"}
        self._update_user(self.USER_HASH, update)
        expected = {"email": "test@example.com", "name": "example", "roles": ["user"]}
        ret_val = self._get_user(self.USER_HASH)
        j = self._get_json(ret_val)
        self.assertEqual(j, expected)

    def test_update_user_unexpected_field(self):
        data = {"email": "test@example.com"}
        self._put_user(self.USER_HASH, data)
        update = {"email": "test@example.com", "bad_field": "1"}
        self._update_user(self.USER_HASH, update, expected_status=400)

    def test_delete_user(self):
        data = {"email": "test@example.com"}
        self._put_user(self.USER_HASH, data)
        ret_val = self._delete_user(self.USER_HASH)
        ret_val = self._get_user(self.USER_HASH, expected_status=404)

    def test_delete_user(self):
        ret_val = self._delete_user(self.USER_HASH, headers={}, expected_status=405)

    def test_delete_user_missing(self):
        self._delete_user(self.USER_HASH, expected_status=404)
