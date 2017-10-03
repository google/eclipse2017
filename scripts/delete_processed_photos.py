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

"""Deletes processed photos (debug tool)."""

import argparse
from google.cloud import datastore
import common.service_account as sa

# This is not a valid project name (for safety)
DEFAULT_PROJECT = 'eclipse-2017-test'

def get_arguments():
    parser = argparse.ArgumentParser(description='Delete processed photos.')
    parser.add_argument('--project_id', type=str, default=DEFAULT_PROJECT)
    return parser.parse_args()

def main():
    args  = get_arguments()

    client = datastore.Client(project=args.project_id)

    query = client.query(kind="ProcessedImage")
    query.keys_only()

    entities = query.fetch()
    batch = client.batch()
    batch.begin()
    i = 0
    for entity in entities:
        batch.delete(entity.key)
        i = i + 1
        if i == 500:
            batch.commit()
            batch = client.batch()
            batch.begin()
            i = 0
    batch.commit()

if __name__ == '__main__':
    main()
