
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

import hashlib
import logging
import types
import flask

from google.cloud import datastore

from common.eclipse2017_exceptions import MissingCredentialTokenError, MissingUserError, ApplicationIdentityError
from common.secret_keys import GOOGLE_HTTP_API_KEY, GOOGLE_OAUTH2_CLIENT_ID

from app_module import AppModule
from common import util
from common import users
from common import flask_users
from common import roles


REQUIRED_FIELDS = set(())
OPTIONAL_FIELDS = set(('name', 'location', 'geocoded_location', 'camera', 'email', 'badges'))
IMMUTABLE_FIELDS = set(('roles'))
ALL_MUTABLE_FIELDS = set.union(REQUIRED_FIELDS, OPTIONAL_FIELDS)
ALL_FIELDS = set.union(ALL_MUTABLE_FIELDS, IMMUTABLE_FIELDS)

class Profile(AppModule):
    """
    Class for user profile CRUD.
    """
    def __init__(self, hashlib=hashlib, **kwargs):
        super(Profile, self).__init__(**kwargs)

        # Dependency injection
        self.hashlib = hashlib

        self.name = 'profile'
        self.import_name = __name__

        self._routes = (
            ('/', 'root', self.root, ('GET',)),
            ('/<user_id>', 'user', self.user, ('GET', 'PUT', 'UPDATE', 'DELETE')))

    def root(self):
        return flask.Response('OK', status=200)

    def user(self, user_id):
        client = self._get_datastore_client()
        result = flask_users.authn_check(flask.request.headers)
        if isinstance(result, flask.Response):
            return result
        userid_hash = users.get_userid_hash(result)

        # User GETting their own record
        if self.request.method == 'GET':
            if userid_hash == user_id:
                return self.get_user(user_id)
            else:
                return flask.Response('Permission denied', status=403)

        # Special case for user PUTting their own initial record
        if self.request.method == 'PUT' and \
           not users.check_if_user_exists(client, userid_hash) and \
           userid_hash == user_id:
              return self.put_user(user_id)

        # Users can only modify their own records
        if userid_hash != user_id:
            return flask.Response('Permission denied', status=403)

        if self.request.method == 'PUT':
            return self.put_user(user_id)
        elif self.request.method == 'DELETE':
            return self.delete_user(user_id)
        elif self.request.method == 'UPDATE':
            return self.update_user(user_id)
        else:
          return flask.Response('Unsupported method', status=405)

    def get_user(self, user_id):
        client = self._get_datastore_client()

        try:
            entity = users.get_user(client, user_id)
        except Exception as e:
            logging.error("Datastore get operation failed: %s" % str(e))
            return flask.Response('Internal server error', status=500)

        if entity is None:
            return flask.Response('User does not exist', status=404)
        if not roles._check_if_user_role_exists(client, user_id):
            return flask.Response('User role does not exist', status=404)
        roles_ = roles.get_user_role(client, user_id)
        result = self._create_user_dict(entity, roles_)
        s = flask.jsonify(**result)
        return s

    def put_user(self, user_id):
        client = self._get_datastore_client()

        result = util._validate_json(flask.request)
        if result is not True:
            return result
        json = flask.request.get_json()
        json = util._escape_json(json)
        result = self._validate_create_user(user_id, json)
        if result is not True:
            return result
        result = self._validate_fields(json)
        if result is not True:
            return result

        with client.transaction():
            try:
                if users.check_if_user_exists(client, user_id):
                    return self.Response('User exists', status=409)
                entity = users.get_empty_user_entity(client, user_id)
                util._update_entity(json, ALL_MUTABLE_FIELDS, entity)
                users.create_or_update_user(client, entity)
                roles.create_user_role(client, user_id)
            except Exception as e:
                logging.error("Datastore put operation failed: %s" % str(e))
                self.Response('Internal server error', status=500)

        return self.Response('OK', status=200)

    def update_user(self, user_id):
        client = self._get_datastore_client()

        result = util._validate_json(flask.request)
        if result is not True:
            return result
        json = flask.request.get_json()
        json = util._escape_json(json)
        result = self._validate_update_user(user_id, json)
        if result is not True:
            return result
        result = self._validate_fields(json)
        if result is not True:
            return result

        with client.transaction():
            try:
                entity = users.get_user(client, user_id)
                if entity is None:
                    return flask.Response('User does not exist', status=404)
                util._update_entity(json, ALL_MUTABLE_FIELDS, entity)
                users.create_or_update_user(client, entity)
            except Exception as e:
                logging.error("Datastore update operation failed: %s" % str(e))
                flask.Response('Internal server error', status=500)
        return flask.Response('OK', status=200)

    def delete_user(self, user_id):
        client = self._get_datastore_client()

        with client.transaction():
            try:
                if not users.check_if_user_exists(client, user_id):
                    return flask.Response('User does not exist', status=404)
                users.delete_user(client, user_id)
                roles.delete_user_role(client, user_id)
            except Exception as e:
                logging.error("Datastore delete operation failed: %s" % str(e))
                flask.Response('Internal server error', status=500)
        return flask.Response('OK', status=200)

    def _validate_fields(self, json):
        # TODO(dek): consider making a schema with types
        if 'tos_accepted' in json and type(json['tos_accepted']) is not types.IntType:
            return flask.Response('tos_accepted field must be an integer', status=405)
        return True

    def _validate_create_user(self, user_id, json):
        """Returns True if all REQUIRED_FIELDS are present in json, and all fields are in ALL_MUTABLE_FIELDS."""
        fields = set([field for field in json])
        s = REQUIRED_FIELDS - fields
        if len(s):
            missing = ', '.join(s)
            return flask.Response('Invalid input (missing required field(s): %s)' % missing, status=400)
        s = fields - ALL_MUTABLE_FIELDS
        if len(s):
            unexpected = ', '.join(s)
            return flask.Response('Invalid input (unexpected field(s): %s)' % unexpected, status=400)
        return True

    def _validate_update_user(self, user_id, json):
        """Returns True if at least one of ALL_MUTABLE_FIELDS are present in json."""
        fields = set([field for field in json])
        if len(ALL_MUTABLE_FIELDS.intersection(fields)) == 0:
            options = ', '.join(ALL_MUTABLE_FIELDS)
            return flask.Response('Invalid input (missing at least one field from %s)' % options, status=400)
        s = fields - ALL_MUTABLE_FIELDS
        if len(s):
            unexpected = ', '.join(s)
            return flask.Response('Invalid input (unexpected field(s): %s)' % unexpected, status=400)
        return True

    def _create_user_dict(self, entity, roles):
        result = {}
        for field in ALL_FIELDS:
            if field in entity:
                result[field] = entity[field]
        result['roles'] = roles
        return result

profile = Profile()
