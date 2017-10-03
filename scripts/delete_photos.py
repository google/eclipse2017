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

"""Deletes uploaded photos (debug tool)."""

import argparse
from google.cloud import datastore
import common.service_account as sa
from common.chunks import chunks

# This is not a valid project name (for safety)
DEFAULT_PROJECT = 'eclipse-2017-test'

def get_arguments():
    parser = argparse.ArgumentParser(description='Delete uploaded photos.')
    parser.add_argument('--project_id', type=str, default=DEFAULT_PROJECT)
    parser.add_argument('--upload_session_id', type=str, default=None)
    parser.add_argument('--user_id', type=str, default=None)
    return parser.parse_args()

def main():
    args  = get_arguments()

    client = datastore.Client(project=args.project_id)

    query = client.query(kind="Photo")
    query.keys_only()

    if args.upload_session_id != None:
        query.add_filter('upload_session_id', '=', args.upload_session_id)
    if args.user_id != None:
        print client.key(u'User', unicode(args.user_id))
        query.add_filter('user', '=', client.key('User', args.user_id))


    entities = list(query.fetch())
    entity_chunks = chunks(entities, 500)
    for entity_chunk in entity_chunks:
        print "creating batch"
        batch = client.batch()
        batch.begin()
        for entity in entity_chunk:
            batch.delete(entity.key)
        batch.commit()
        print "batch committed"

if __name__ == '__main__':
    main()
