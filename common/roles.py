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

ADMIN_ROLE = 'admin'
USER_ROLES = set(('user', ADMIN_ROLE, 'asp'))
from common import util
from common import test_common

import flask
from gcloud.exceptions import GCloudError
from common.eclipse2017_exceptions import MissingUserError
from gcloud import datastore
import logging

class Roles:
    """
    Class for roles profile CRUD.
    """
    def __init__(self):
        pass

    def get_all_user_roles(self, client):
        query = client.query(kind="UserRole")
        query = query.fetch()
        entities = list(query)
        results = {}
        for entity in entities:
            user_id = entity.key.id_or_name
            results[user_id] = entity['roles']
        return results

    def get_user_role(self, client, user_id):
        key = client.key("UserRole", user_id)
        entity = client.get(key)
        if entity is None:
          raise MissingUserError
        return entity['roles']

    def create_user_role(self, client, user_id, roles=[u'user']):
        try:
            if self._check_if_user_role_exists(client, user_id):
                return False
            key = client.key("UserRole", user_id)
            entity = datastore.Entity(key=key)
            entity['roles'] = roles
            client.put(entity)
        except GCloudError as e:
            logging.error("Datastore update operation failed: %s" % str(e))
            return False
        return True

    def update_user_role(self, client, user_id, new_roles=[u'user']):
        try:
            if not self._check_if_user_role_exists(client, user_id):
                return False
            key = client.key("UserRole", user_id)
            entity = client.get(key)
            entity['roles'] = new_roles
            client.put(entity)
        except GCloudError as e:
            logging.error("Datastore update operation failed: %s" % str(e))
            return False
        return True

    def delete_user_role(self, client, user_id):
        try:
            if not self._check_if_user_role_exists(client, user_id):
                return False
            key = client.key("UserRole", user_id)
            client.delete(key)
        except GCloudError as e:
            logging.error("Datastore update operation failed: %s" % str(e))
            return False
        return True

    class RolesNotInJSON(Exception):
        pass

    def _validate_fields(self, json):
        if 'roles' not in json:
            raise RolesNotInJSON
        if not isinstance(json['roles'], list):
            raise ValueError
        return True

    def _check_if_user_role_exists(self, client, user_id):
        """Returns True if User with user_id already exists."""
        key = client.key("UserRole", user_id)
        entity = client.get(key)

        return entity is not None


    def _check_if_user_is_admin(self, client, userid_hash):
        return ADMIN_ROLE in self.get_user_role(client, userid_hash)

    def _authr_check(self, userid_hash):
        try:
            user_roles = self.roles.get_user_role(self._get_datastore_client(), userid_hash)
        except MissingUserError:
            return flask.Response('Missing user role', status=404)
        except GCloudError as e:
            return flask.Response('Backend error', status=500)

        return user_roles
