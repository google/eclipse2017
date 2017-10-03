
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

import datetime
import hashlib
import types
import flask
import logging

from google.cloud import datastore, storage

from common import config
from common.eclipse2017_exceptions import MissingCredentialTokenError, MissingUserError, ApplicationIdentityError
from common.secret_keys import GOOGLE_HTTP_API_KEY, GOOGLE_OAUTH2_CLIENT_ID, IDEUM_APP_SECRET

from app_module import AppModule
from common import util
from common import users
from common import flask_users
from common import roles
from common.chunks import chunks
from common.image_sorter import pick_image

from common import repair_missing_gps

FIELDS = set(('lat', 'lon', 'image_datetime', 'uploaded_date', 'url', 'image_type', 'num_reviews', 'image_bucket'))


class Photo(AppModule):
    """
    Class for user photo CRUD.
    """
    def __init__(self, hashlib=hashlib, **kwargs):
        super(Photo, self).__init__(**kwargs)

        # Dependency injection
        self.hashlib = hashlib

        self.name = 'photo'
        self.import_name = __name__

        self._routes = (
            ('/', 'root', self.root, ('GET',)),
            ('/confirm', 'confirm', self.confirm, ('POST',)),
            ('/<photo_id>', 'photo', self.photo, ('GET','PATCH')))

    def root(self, cursor=None):
        """Returns list of photos subject to filter criteria."""
        client = self._get_datastore_client()

        # Auth check: must be logged in, user profile exists, have
        # admin or reviewer role
        result = flask_users.authn_check(flask.request.headers)
        if isinstance(result, flask.Response):
            return result
        userid_hash = users.get_userid_hash(result)
        if not users.check_if_user_exists(client, userid_hash):
            return flask.Response('User does not exist', status=404)
        result = roles._check_if_user_has_role(client, userid_hash, set([roles.ADMIN_ROLE, roles.REVIEWER_ROLE]))
        if isinstance(result, flask.Response):
            return result
        if result is False:
            return flask.Response('Permission denied', status=403)

        # Check if cursor passed in from clinet
        cursor = flask.request.args.get('cursor', None)
        if cursor is not None:
            cursor = str(cursor)

        # Filter, and order, items.
        order = []
        filters = []
        num_reviews_max = flask.request.args.get('num_reviews_max', None)
        if num_reviews_max is not None:
            filters.append(('num_reviews', '<=', int(num_reviews_max)))
            order.append('num_reviews')
        mask_reviewer = flask.request.args.get('mask_reviewer', False)
        image_bucket = flask.request.args.get('image_bucket', None)
        if image_bucket is not None:
            filters.append(('image_bucket', '=', image_bucket))
            order.append('image_bucket')
        user_id = flask.request.args.get('user_id', None)
        if user_id is not None:
            filters.append(('user', '=', client.key("User", user_id)))
            order.append('user')
        upload_session_id = flask.request.args.get('upload_session_id', None)
        if upload_session_id is not None:
            filters.append(('upload_session_id', '=', upload_session_id))
            order.append('upload_session_id')

        if flask.request.args.get('image_datetime_begin'):
            image_datetime_begin = datetime.datetime.fromtimestamp(float(flask.request.args['image_datetime_begin']))
            filters.append(('image_datetime', '>', image_datetime_begin))
            order.append('image_datetime')
        if flask.request.args.get('image_datetime_end'):
            image_datetime_end = datetime.datetime.fromtimestamp(float(flask.request.args['image_datetime_end']))
            filters.append(('image_datetime', '<=', image_datetime_end))
            if 'image_datetime' not in order:
                order.append('image_datetime')
        if flask.request.args.get('uploaded_date_begin'):
            uploaded_date_begin = datetime.datetime.fromtimestamp(float(flask.request.args['uploaded_date_begin']))
            filters.append(('uploaded_date', '>', uploaded_date_begin))
            order.append('uploaded_date')
        if flask.request.args.get('uploaded_date_end'):
            uploaded_date_end = datetime.datetime.fromtimestamp(float(flask.request.args['uploaded_date_end']))
            filters.append(('uploaded_date', '<=', uploaded_date_end))
            if 'uploaded_date' not in order:
                order.append('uploaded_date')

        # TODO(dek): randomize results(?)

        # Fetch start_cursor to limit entites
        query = client.query(kind="Photo", filters=filters)
        query.order = order
        limit = int(flask.request.args.get('limit', 100))
        entities = query.fetch(start_cursor=cursor, limit=limit)
        page = next(entities.pages)
        # Fetch results before getting next page token
        e = list(page)
        next_cursor = entities.next_page_token

        if e is None:
            return flask.Response('No entities.', 200)
        # Return matching photos by ID
        photos = []
        client = storage.client.Client(project=config.PROJECT_ID)
        bucket = client.bucket(config.GCS_BUCKET)
        for entity in e:
            blob = storage.Blob(entity.key.name, bucket)
            url = blob.public_url
            if 'image_type' not in entity:
                logging.error("Photo %s does not have an image type." % entity.key.name)
                continue
            include_photo = True
            location = None
            if 'lat' in entity and 'lon' in entity:
                location = {"lat": entity['lat'], "lon": entity['lon']}

            if entity['image_type'] == 'raw' or entity['image_type'] == 'TIFF':
                # If the image isn't a JPG, the browser won't show it.
                # Make the URL point at the JPG copy
                url = url + '.jpg'
            if mask_reviewer and entity.has_key("reviews"):
                for review in entity["reviews"]:
                    # Don't consider photos where we satisfy the
                    # num_reviews inequality, but one of the reviewers
                    # is ourself
                    if review['user_id'] == userid_hash:
                        include_photo = False
                        break

            if include_photo:
                photo = {'name': entity.key.name, 'url': url}
                if location is not None:
                    photo['location'] = location
                photos.append(photo)
        results = {}
        if len(photos):
            results['cursor'] = next_cursor
        results['photos'] = photos
        return flask.jsonify(results)

    def photo(self, photo_id):
        """GET returns photo entity, PATCH modifies photo entity."""
        client = self._get_datastore_client()

        # Auth check: must be logged in, user profile exists, have
        # admin or reviewer role
        result = flask_users.authn_check(flask.request.headers)
        if isinstance(result, flask.Response):
            return result
        userid_hash = users.get_userid_hash(result)
        if not users.check_if_user_exists(client, userid_hash):
            return flask.Response('User does not exist', status=404)
        result = roles._check_if_user_has_role(client, userid_hash, set([roles.ADMIN_ROLE, roles.REVIEWER_ROLE]))
        if isinstance(result, flask.Response):
            return result
        if result is False:
            return flask.Response('Permission denied', status=403)

        key = client.key("Photo", str(photo_id))

        # Dispatch on method
        if self.request.method == 'GET':
            # if the photo_id exists, return the approved fields
            result = {}
            entity = client.get(key)
            for field in FIELDS:
                if field not in entity:
                    return flask.Response('Invalid photo (missing field %s)' % field, 404)
                result[field] = entity[field]
            result['reviews'] = []
            for review in entity['reviews']:
                reviewer = review['user_id'].name
                vote = review['vote']
                result['reviews'].append((reviewer, vote))
            result['user'] = entity['user'].name
            return flask.jsonify(result)
        elif flask.request.method == 'PATCH':
            # if the photo_id exists, update it
            result = util._validate_json(flask.request)
            if result is not True:
                return result
            json = flask.request.get_json()
            json = util._escape_json(json)
            if 'vote' not in json:
                return flask.Response('Missing vote', 400)
            vote = json['vote']
            if vote != "up" and vote != "down":
                return flask.Response('Invalid vote, use "up" or "down"', 400)

            with client.transaction():
                # Fetch the existing Photo entity
                entity = client.get(key)
                review = datastore.Entity(key=client.key('Review'))
                review['user_id'] = userid_hash
                review['vote'] = vote
                # Update the reviews property
                if 'reviews' not in entity:
                    # Case: no existing reviews, create first
                    entity["reviews"] = [review]
                else:
                    for r in entity["reviews"]:
                        reviewer_key = r['user_id']
                        # Case: existing review by user, edit vote
                        if reviewer_key == userid_hash:
                            r['vote'] = vote
                        else:
                            # Case: existing review by new user, append
                            entity["reviews"].append(review)
                entity["num_reviews"] = len(entity["reviews"])
                try:
                    client.put(entity)
                except Exception as e:
                    logging.error("Datastore update operation failed: %s" % str(e))
                    flask.Response('Internal server error', status=500)
            return flask.Response('OK', status=200)

    def confirm(self):
        """For each photo from upload_session_id that matches the files from original_filenames, mark it confirmed_by_user=True"""
        client = self._get_datastore_client()
        # Auth check: must be logged in, user profile exists, have
        # admin or volunteer role
        result = flask_users.authn_check(flask.request.headers)
        if isinstance(result, flask.Response):
            return result
        userid_hash = users.get_userid_hash(result)
        if not users.check_if_user_exists(client, userid_hash):
            return flask.Response('User does not exist', status=404)
        if flask.request.headers.has_key("X-IDEUM-APP-SECRET") and flask.request.headers["X-IDEUM-APP-SECRET"] == IDEUM_APP_SECRET:
            logging.info("Request contains Ideum app secret.")
        else:
            result = roles._check_if_user_has_role(client, userid_hash, set([roles.USER_ROLE, roles.ADMIN_ROLE, roles.VOLUNTEER_ROLE]))
            if isinstance(result, flask.Response):
                return result
            if result is False:
                return flask.Response('Permission denied', status=403)

        json = flask.request.get_json()
        if 'upload_session_id' not in json:
            return flask.Response('upload_session_id required', status=403)
        upload_session_id = json['upload_session_id']

        if 'filenames' not in json:
            return flask.Response('filenames required', status=403)
        filenames = json['filenames']
        anonymous_photo = json.get('anonymous_photo', False)
        equatorial_mount = json.get('equatorial_mount', False)

        filters = [('upload_session_id', '=', upload_session_id)]
        query = client.query(kind="Photo", filters=filters)
        entities = list(query.fetch())
        results = repair_missing_gps.partition_gps(entities)
        complete_images, incomplete_images = results
        all_entities = complete_images[:]
        # If there's one complete image and more than one incomplete images,
        # repair the incomplete images using the complete image
        logging.info("Received %d complete images" % len(complete_images))
        logging.info("Received %d incomplete images" % len(incomplete_images))
        if len(incomplete_images) > 0:
            logging.info("Repairing incomplete images: %s" % str(incomplete_images))
            if complete_images == []:
                complete_image = None
            else:
                complete_image = pick_image(complete_images)
            logging.info("Chose %s as complete image" % complete_image)
            for incomplete_image in incomplete_images:
                repaired_image = repair_missing_gps.update_incomplete(complete_image, incomplete_image)
                all_entities.append(repaired_image)
            logging.info("Repaired: %s" % ([incomplete_image.key.name for incomplete_image in incomplete_images]))
            if complete_image is not None:
                logging.info("Repair source: %s", complete_image.key.name)
        else:
            for incomplete_image in incomplete_images:
                all_entities.append(incomplete_image)
            logging.info("No repairs for: %s" % [incomplete_image.key.name for incomplete_image in incomplete_images])

        for entity_chunk in chunks(all_entities, 500):
            batch = client.batch()
            batch.begin()
            for entity in entity_chunk:
                if entity.has_key(u'original_filename') and entity[u'original_filename'] in filenames:
                    entity['confirmed_by_user'] = True
                    entity['anonymous_photo'] = anonymous_photo
                    entity['equatorial_mount'] = equatorial_mount
                    batch.put(entity)

            batch.commit()
        return flask.Response('OK', status=200)


photo = Photo()
