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


class PhotoCount(AppModule):
  """
  Class for photo count.
  """
  def __init__(self, *args, **kwargs):
    super(PhotoCount, self).__init__(*args, **kwargs)
    self.name = 'photo_count'
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

    filters = []
    image_bucket = flask.request.args.get('image_bucket', None)
    if image_bucket is not None:
      filters.append(('image_bucket', '=', image_bucket))

    filters.append(('confirmed_by_user', '=', True))

    total_count = 0
    gps_count = 0
    type_count = {'app': {'total_count': 0, 'gps_count': 0},
                  'volunteer_test': {'total_count': 0, 'gps_count': 0},
                  'megamovie': {'total_count': 0, 'gps_count': 0},
                  'teramovie': {'total_count': 0, 'gps_count': 0}}
    query = client.query(kind="Photo", filters=filters)
    cursor = None
    while True:
      entities_count = 0
      entities = query.fetch(start_cursor=cursor, limit=1000)
      for entity in entities:
        entities_count += 1
        image_bucket = entity['image_bucket']
        type_counter = type_count.get(image_bucket, None)
        if type_counter is not None:
          type_counter['total_count'] += 1

        if entity.has_key('lat') and entity.has_key('lon'):
          if type_counter is not None:
            type_counter['gps_count'] += 1
          gps_count += 1

      total_count += entities_count
      if entities_count < 1000:
        break
      cursor = entities.next_page_token

    photo_stats = {'total_count': total_count, 'gps_count': gps_count,
                   'types': type_count}
    s = flask.jsonify(photo_stats)
    return s

photo_count = PhotoCount()
