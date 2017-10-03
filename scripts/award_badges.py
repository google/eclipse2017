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

"""Script to create user badges."""

import argparse
import glob
import os
from google.cloud import datastore
from common.chunks import chunks

def get_arguments():
    parser = argparse.ArgumentParser(description='Assigns badges to users')
    parser.add_argument('--dry_run', dest='dry_run', action='store_true')
    parser.add_argument('--project_id', type=str, default="eclipse-2017-test")
    return parser.parse_args()

def main():
    args  = get_arguments()
    client = datastore.Client(project=args.project_id)
    if args.dry_run is False:
      print "Really awarding badges"

    filters = []
    filters.append(('confirmed_by_user', '=', True))

    user_count = {}
    # Get photo counts by user.
    query = client.query(kind="Photo", filters=filters)
    cursor = None
    while True:
      entities_count = 0
      entities = query.fetch(start_cursor=cursor, limit=1000)
      for entity in entities:
        entities_count += 1
        user_id = entity['user'].name
        user_counter = user_count.get(user_id, None)
        if user_counter is None:
          user_counter = {'total_count' : 0}
          user_count[user_id] = user_counter

        user_counter['total_count'] += 1

      if entities_count < 1000:
        break
      cursor = entities.next_page_token

    # Now loop through the user table and give badges based on data.
    query = client.query(kind="User")
    cursor = None
    badge_stats = {u'ul1' : 0, u'ul2': 0, u'ul5' : 0, u'ul10' : 0, u'ul25' : 0, u'ul50' : 0,
        u'ul100' : 0, u'ul250' : 0, u'ul500' : 0}
    while True:
      entities_count = 0
      entities = query.fetch(start_cursor=cursor, limit=1000)
      for entity in entities:
        entities_count += 1
        user_id = entity.key.name
        user_counter = user_count.get(user_id, None)

        if user_counter is not None:
          photo_count = user_counter['total_count']
          count_badge = None
          if photo_count >= 500:
              count_badge = u'ul500'
          elif photo_count >= 250:
              count_badge = u'ul250'
          elif photo_count >= 100:
              count_badge = u'ul100'
          elif photo_count >= 50:
              count_badge = u'ul50'
          elif photo_count >= 25:
              count_badge = u'ul25'
          elif photo_count >= 10:
              count_badge = u'ul10'
          elif photo_count >= 5:
              count_badge = u'ul5'
          elif photo_count >= 2:
              count_badge = u'ul2'
          elif photo_count == 1:
              count_badge = u'ul1'

          if count_badge is not None:
            if args.dry_run is True:
              print "Awarding badge ", count_badge, " to ", user_id
            else:
              entity['badges'] = [count_badge]
              client.put(entity)
            badge_stats[count_badge] += 1

      if entities_count < 1000:
        break
      cursor = entities.next_page_token

    print "Badge counts", badge_stats

if __name__ == '__main__':
    main()
