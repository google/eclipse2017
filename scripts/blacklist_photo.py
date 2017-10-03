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

"""Blacklist photos"""

import argparse
from google.cloud import datastore

DEFAULT_PROJECT = 'eclipse-2017-test'

def get_arguments():
    parser = argparse.ArgumentParser(description='Blacklist photos.')
    parser.add_argument('--project_id', type=str, default=DEFAULT_PROJECT,
                        help = 'Project ID to apply updates to')
    parser.add_argument('--photo_id_file', type=str,
                        help = 'File of photo ids to apply updates to (combined with --photo_id)')
    parser.add_argument('--photo_id', type=str,
                        help = 'Single photo id to apply updates to (combined with --photo_id_file)')
    parser.add_mutually_exclusive_group(required=False)
    parser.add_argument('--blacklist', dest='blacklist', action='store_true')
    parser.add_argument('--no-blacklist', dest='blacklist', action='store_false')
    return parser.parse_args()

def main():
    args  = get_arguments()

    client = datastore.Client(args.project_id)

    photo_ids = []
    if args.photo_id_file:
        f = open(args.photo_id_file)
        photo_ids.extend([line.strip() for line in f.readlines()])
    if args.photo_id:
        photo_ids.append(args.photo_id)

    print photo_ids
    for photo_id in photo_ids:
        key = client.key("Photo", photo_id)
        entity = client.get(key)
        if entity is None:
            print "No such photo:", photo_id
        else:
            print "saving blacklist:", args.blacklist
            entity['blacklisted'] = args.blacklist
            client.put(entity)


if __name__ == '__main__':
    main()
