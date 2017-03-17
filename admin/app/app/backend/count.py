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

import flask

from gcloud.exceptions import GCloudError
from gcloud import datastore

from app_module import AppModule
from common import roles
from common import users


class Count(AppModule):
    """
    Class for user count.
    """
    def __init__(self, *args, **kwargs):
        super(Count, self).__init__(*args, **kwargs)
        self.name = 'count'
        self.import_name = __name__
        self.users = users.Users()
        self.roles = roles.Roles()

        self._routes = (
            ('/', 'root', self.root, ('GET',)),)

    def root(self):
        client = self._get_datastore_client()
        result = self.users.authn_check(flask.request.headers)
        if isinstance(result, flask.Response):
            return result
        userid_hash = self.users.get_userid_hash(result)
        if not self.users.check_if_user_exists(client, userid_hash):
            return flask.Response('User does not exist', status=404)
        result = self.roles._check_if_user_is_admin(client, userid_hash)
        if isinstance(result, flask.Response):
            return result
        if result is False:
            return flask.Response('Permission denied', status=403)
        query = client.query(kind="User")
        query.keys_only()
        entities = query.fetch()
        l = len(list(entities))
        return flask.Response(str(l), status=200)

count = Count()
