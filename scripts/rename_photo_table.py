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

import argparse
from common.chunks import chunks
from google.cloud import datastore

def get_arguments():
    parser = argparse.ArgumentParser(description='Rename the PhotoTable')
    parser.add_argument('--project_id', type=str, default="eclipse-2017-test")
    return parser.parse_args()

def main():
    args  = get_arguments()

    client = datastore.Client(project=args.project_id)

    # Fetch all keys of the new Photo table
    query = client.query(kind="PhotoVolunteerTest")
    query.keys_only()

    cursor = None
    results = []
    while True:
        entities = query.fetch(start_cursor=cursor, limit=1000)
        l = list(entities)
        results.extend(l)
        if len(l) < 1000:
            break
        cursor = entities.next_page_token

    # Delete all keys in the PhotoVolunteerTest table
    result_chunks = chunks(results, 500)
    for result_chunk in result_chunks:
        batch = client.batch()
        batch.begin()
        for result in result_chunk:
            batch.delete(result.key)
        batch.commit()

    # Fetch all keys of the old Photo table
    query = client.query(kind="Photo")

    cursor = None
    results = []
    while True:
        entities = query.fetch(start_cursor=cursor, limit=1000)
        l = list(entities)
        results.extend(l)
        if len(l) < 1000:
            break
        cursor = entities.next_page_token

    # Copy all the keys from the Photo table to the PhotoVolunteerTest table
    result_chunks = chunks(results, 500)
    for result_chunk in result_chunks:
        batch = client.batch()
        batch.begin()
        for result in result_chunk:
            key = client.key("PhotoVolunteerTest", result.key.name)
            entity = datastore.Entity(key=key)
            # Fix datetimes not roundtripping properly (they are missing tz info)
            entity.update(result)
            batch.put(entity)
        batch.commit()


if __name__ == '__main__':
    main()
