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

from google.cloud import datastore

from app_module import AppModule
from common import roles
from common import users
from common import flask_users


class Count(AppModule):
    """
    Class for user count.
    """
    def __init__(self, *args, **kwargs):
        super(Count, self).__init__(*args, **kwargs)
        self.name = 'count'
        self.import_name = __name__

        self._routes = (
            ('/', 'root', self.root, ('GET',)),)

    def root(self):
        client = self._get_datastore_client()
        result = flask_users.authn_check(flask.request.headers)
        if isinstance(result, flask.Response):
            return result
        userid_hash = users.get_userid_hash(result)
        if not users.check_if_user_exists(client, userid_hash):
            return flask.Response('User does not exist', status=404)
        result = roles._check_if_user_is_admin(client, userid_hash)
        if isinstance(result, flask.Response):
            return result
        if result is False:
            return flask.Response('Permission denied', status=403)

        total_count = 0
        volunteer_count = 0
        query = client.query(kind="UserRole")
        cursor = None
        while True:
            entities_cnt = 0
            entities = query.fetch(start_cursor=cursor, limit=1000)
            for entity in entities:
                entities_cnt += 1
                if u"volunteer" in entity['roles']:
                    volunteer_count += 1

            total_count += entities_cnt
            if entities_cnt < 1000:
                break
            cursor = entities.next_page_token

        results = {"total_count" : total_count,
                   "volunteer_count" : volunteer_count}
        return flask.jsonify(results)

count = Count()
