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

"""Extract all metadata from datastore and cache in local pickle files."""

import os
import pickle
import datetime
from google.cloud import datastore
import argparse
import pytz
import metadata

DEFAULT_PROJECT = 'eclipse-2017-test'

def get_arguments():
    parser = argparse.ArgumentParser(description='Extract metadata.')
    parser.add_argument('--project_id', type=str, default=DEFAULT_PROJECT)
    parser.add_argument('--photo_metadata', type=str, default="photo_metadata.pkl")
    parser.add_argument('--user_metadata', type=str, default="user_metadata.pkl")
    parser.add_argument('--directory', type=str, default="photos")
    return parser.parse_args()

def main():
    args  = get_arguments()
    client = datastore.Client(project=args.project_id)

    query = client.query(kind='Photo')
    entities = list(query.fetch())
    pickle.dump(entities, open(args.photo_metadata, "wb"))

    query = client.query(kind='User')
    entities = list(query.fetch())
    pickle.dump(entities, open(args.user_metadata, "wb"))

if __name__ == '__main__':
    main()
