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

"""Print list of users (debug tool)."""

import argparse
from google.cloud import datastore
import common.service_account as sa

DEFAULT_PROJECT = 'eclipse-2017-test-147301'

def get_arguments():
    parser = argparse.ArgumentParser(description='Print list of users.')
    parser.add_argument('--project_id', type=str, default=DEFAULT_PROJECT)
    return parser.parse_args()

def main():
    args  = get_arguments()

    client = datastore.Client(project=args.project_id)

    query = client.query(kind="User")

    entities = query.fetch()
    for entity in entities:
        print "User id (hashed):", entity.key.name
        if 'badges' in entity:
            print "Badges ", entity['badges']
        key = client.key("UserRole", entity.key.name)
        entity = client.get(key)
        print "\troles:", entity['roles']

if __name__ == '__main__':
    main()
