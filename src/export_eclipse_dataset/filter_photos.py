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

"""Filter photos based on criteria."""

import os
import pickle
import datetime
import argparse
import pytz
import metadata

DEFAULT_PROJECT = 'eclipse-2017-test'

def get_arguments():
    parser = argparse.ArgumentParser(description='Filter photos based on criteria.')
    parser.add_argument('--project_id', type=str, default=DEFAULT_PROJECT)
    parser.add_argument('--photo_metadata', type=str, default="photo_metadata.pkl")
    parser.add_argument('--filtered_photo_metadata', type=str, default="filtered_photo_metadata.pkl")
    parser.add_argument('--directory', type=str, default="photos")
    return parser.parse_args()

def main():
    args  = get_arguments()

    entities = pickle.load(open(args.photo_metadata, "rb"))
    filtered_entities = [entity for entity in entities if metadata.filter_photo_record(entity)]
    pickle.dump(filtered_entities, open(args.filtered_photo_metadata, "wb"))

if __name__ == '__main__':
    main()
