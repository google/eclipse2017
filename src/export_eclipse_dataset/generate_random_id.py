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

import uuid
import os
import pickle
import datetime
from google.cloud import datastore
import argparse
import pytz
import metadata


def get_arguments():
    parser = argparse.ArgumentParser(description='Generate mapping table from ID to random UUID.')
    parser.add_argument('--user_metadata', type=str, default="user_metadata.pkl")
    parser.add_argument('--user_random_uuid', type=str, default="user_random_uuid.pkl")
    return parser.parse_args()

def main():
    args  = get_arguments()
    user_metadata = pickle.load(open(args.user_metadata, "rb"))
    r = {}
    for user in user_metadata:
        r[user.key.name] = uuid.uuid4().get_hex()
    pickle.dump(r, open(args.user_random_uuid, "wb"))

if __name__ == '__main__':
    main()
