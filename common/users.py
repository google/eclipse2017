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

import hashlib
from common import util
from common import test_common
from google.cloud import datastore

from common.eclipse2017_exceptions import MissingCredentialTokenError, MissingUserError
def get_id_token(headers):
    if 'X-IDTOKEN' not in headers:
        raise MissingCredentialTokenError
    return headers['X-IDTOKEN']

def get_userid(idinfo):
    if 'sub' not in idinfo:
        raise MissingUserError
    return idinfo["sub"]

def get_userid_hash(userid):
    return unicode(hashlib.sha256(userid).hexdigest())

def get_empty_user_entity(client, user_id):
    key = client.key("User", user_id)
    entity = datastore.Entity(key=key)
    return entity

def get_user(client, user_id):
    """Returns user entity."""
    key = client.key("User", user_id)
    entity = client.get(key)
    return entity

def check_if_user_exists(client, user_id):
    """Returns True if User with user_id already exists."""
    return get_user(client, user_id) is not None

def create_or_update_user(client, entity):
    client.put(entity)

def delete_user(client, user_id):
    key = client.key("User", user_id)
    client.delete(key)
