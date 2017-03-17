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

import flask
import hashlib
from common import util
from common import test_common
from common.eclipse2017_exceptions import MissingCredentialTokenError, MissingUserError, ApplicationIdentityError
from gcloud import datastore

class Users:
    """
    Class for roles profile CRUD.
    """
    def _init__(self):
        pass


    def get_id_token(self, headers):
        if 'X-IDTOKEN' not in headers:
            raise MissingCredentialTokenError
        return headers['X-IDTOKEN']

    def get_userid(self, idinfo):
        if 'sub' not in idinfo:
            raise MissingUserError
        return idinfo["sub"]

    def get_userid_hash(self, userid):
        return unicode(hashlib.sha256(userid).hexdigest())

    def get_empty_user_entity(self, client, user_id):
        key = client.key("User", user_id)
        entity = datastore.Entity(key=key)
        return entity

    def get_user(self, client, user_id):
        """Returns user entity."""
        key = client.key("User", user_id)
        entity = client.get(key)
        return entity

    def check_if_user_exists(self, client, user_id):
        """Returns True if User with user_id already exists."""
        return self.get_user(client, user_id) is not None

    def create_or_update_user(self, client, entity):
        client.put(entity)

    def delete_user(self, client, user_id):
        key = client.key("User", user_id)
        client.delete(key)

    def authn_check(self, headers):
        try:
            token = self.get_id_token(headers)
        except MissingCredentialTokenError:
            return flask.Response("The request is missing a credential token.", 405)
        try:
            idinfo = util._validate_id_token(token)
        except ApplicationIdentityError:
            return flask.Response("The request id token is invalid.", 405)
        try:
            userid = self.get_userid(idinfo)
        except MissingUserError:
            return flask.Response("The user is missing.", 405)
        return userid
