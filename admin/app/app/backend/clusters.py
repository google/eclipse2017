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
from common.cluster_points import cluster_points, compute_centers


class Clusters(AppModule):
    """
    Class for clustered user and photo locations.
    """
    def __init__(self, **kwargs):
        super(Clusters, self).__init__(**kwargs)
        self.name = 'clusters'
        self.import_name = __name__

        self._routes = (
            ('/', 'root', self.root, ('GET',)),
            ('/photos', 'photos', self.photos, ('GET',)),
            ('/users', 'users', self.users, ('GET',)),)

    def root(self):
        return flask.Response('ok')

    def users(self):
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

        locations = []
        query = client.query(kind="User")
        cursor = None
        while True:
            entities_count = 0
            entities = query.fetch(start_cursor=cursor, limit=1000)
            for entity in entities:
                entities_count += 1
                if entity.has_key('geocoded_location'):
                    location = entity['geocoded_location']
                    locations.append(location)

            if entities_count < 1000:
                break
            cursor = entities.next_page_token
        clusters = cluster_points(locations, eps=0.1, min_samples=10, n_jobs=64)
        centers, sizes = compute_centers(clusters, locations)
        results = { 'points': [] }
        if len(centers) != 0:
            results['min_size'] = min(sizes.values())
            results['max_size'] = max(sizes.values())
            p = results['points']
            for label in centers:
                center = centers[label]
                size = sizes[label]
                p.append( ((center[0], center[1]), size))
        return flask.jsonify(results)

    def photos(self):
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
        filters.append(('confirmed_by_user', '=', True))

        image_buckets = flask.request.args.get('image_buckets', "").split(",")

        locations = []
        query = client.query(kind="Photo", filters=filters)
        cursor = None
        while True:
            entities_count = 0
            entities = query.fetch(start_cursor=cursor, limit=1000)
            for entity in entities:
                entities_count += 1
                if entity.has_key('lat') and entity.has_key('lon'):
                    # Negate longitude because photo longitude is stored as positive-West, but
                    # code needs negative-West.
                    location = entity['lat'], -entity['lon']
                    if len(image_buckets) == 0:
                        should_append = True
                    else:
                        # Check if this bucket is in the list.
                        should_append = entity['image_bucket'] in image_buckets

                    if should_append:
                        locations.append(location)

            if entities_count < 1000:
                break
            cursor = entities.next_page_token

        if len(locations) > 0:
            clusters = cluster_points(locations, eps=0.1, min_samples=10, n_jobs=64)
            centers, sizes = compute_centers(clusters, locations)
        else:
            centers = []
            sizes = []

        results = { 'points': [] }
        if len(centers) != 0:
            results['min_size'] = min(sizes.values())
            results['max_size'] = max(sizes.values())
            p = results['points']
            for label in centers:
                center = centers[label]
                size = sizes[label]
                p.append( ((center[0], center[1]), size) )
        return flask.jsonify(results)

clusters = Clusters()
