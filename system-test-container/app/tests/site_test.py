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

import logging
import socket
import time
import unittest2
import requests

from google.cloud import datastore
from google.oauth2 import id_token
from common import constants
from common import git_tag
from common.id_token import get_id_token
from common import users
from common import roles
from common import util
from google.auth.transport import requests as gat_requests

logging.basicConfig(level=logging.INFO, format=constants.LOG_FMT_M_THREADED)

PROJECT_ID = 'eclipse-2017-dev-dek'

class SiteTest(unittest2.TestCase):
    """
    Basic site test
    """
    READINESS_PROBE_PATH = '/'
    NUM_WORKERS = 7
    NUM_REQUESTS = 1

    def __init__(self, *args, **kwargs):
        super(SiteTest, self).__init__(*args, **kwargs)
    def setUp(self):
        self.client = datastore.Client(PROJECT_ID)


    def _get_uri(self, host, port, path, request_headers = {'content-type': 'text/plain'}, expected_data = None, accepted_status_codes = (constants.HTTP_OK,), timeout = 60):
        try:
            r = requests.get("http://%s:%d/%s" % (host, port, path))
        except requests.exceptions.ConnectionError:
            msg = 'Cannot contact server: {0}'.format(host)
            logging.error(msg)
            return False

        if r.status_code not in accepted_status_codes:
            msg = 'Unexpected status code: {0}'.format(r.status)
            logging.error(msg)
            return False

        elif r.status_code != constants.HTTP_OK:
            msg = 'Server returned error: {0}'.format(num_mbytes)
            logging.error(msg)
            return False

        if expected_data is not None:
            if r.text != expected_data:
                logging.error("Expected data: %s was not matched by received data: %s" % (expected_data, data))
                return False
        return True

    def test_get_static(self):
        STATIC_NGINX_HOST = 'static-nginx'
        ADMIN_NGINX_HOST = 'admin-nginx'
        PROFILE_NGINX_HOST = 'profile-nginx'

        NGINX_PORT = 80
        SERVER_PORT = 8080

        for case in [
            { 'host': STATIC_NGINX_HOST, 'port': NGINX_PORT, 'path':  '/' },
            { 'host': STATIC_NGINX_HOST, 'port': NGINX_PORT, 'path': '/hash.html', 'expected_data': git_tag.GIT_TAG},
            { 'host': ADMIN_NGINX_HOST, 'port': NGINX_PORT, 'path': '/', 'expected_data': 'OK' },
            { 'host': PROFILE_NGINX_HOST, 'port': NGINX_PORT, 'path': '/', 'expected_data': 'OK' },
        ]:
            logging.info("Test: %s" % case)
            self.assertTrue(self._get_uri(**case))

    def _delete_user_via_datastore_if_exists(self, userid_hash):
        user = users.get_user(self.client, userid_hash)
        if user is not None:
            users.delete_user(self.client, userid_hash)

    def _get_user_via_api(self, userid_hash, token):
        headers =  { 'x-idtoken': token }
        r = requests.get('http://profile-nginx/services/user/profile/%s' % userid_hash,
                          headers = headers)
        print r
        print r.text


    def _create_user_via_datastore(self, userid_hash):
        user = datastore.Entity(key = self.client.key("User", userid_hash))
        user['name'] = u"Test User " + userid_hash
        user['email'] = u"test" + userid_hash + u"@example.com"
        users.create_or_update_user(self.client, user)
        roles.create_user_role(self.client, userid_hash)

    def test_profile_disabled(self):
        token = get_id_token()
        r = gat_requests.Request()
        idinfo = util._validate_id_token(token)
        userid = users.get_userid(idinfo)
        userid_hash = users.get_userid_hash(userid)

        self._delete_user_via_datastore_if_exists(userid_hash)
        self._get_user_via_api(userid_hash, token)
        self._create_user_via_datastore(userid_hash)
        self._get_user_via_api(userid_hash, token)
