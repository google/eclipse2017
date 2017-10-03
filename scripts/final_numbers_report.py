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

import os
import pickle
import datetime
from google.cloud import datastore
from google.cloud import storage
import argparse
import pytz

DEFAULT_PROJECT = 'eclipse-2017-prod'

def get_arguments():
    parser = argparse.ArgumentParser(description='Map image data.')
    parser.add_argument('--project_id', type=str, default=DEFAULT_PROJECT)
    parser.add_argument('--photo_table', type=str, default="Photo")
    parser.add_argument('--image_bucket', type=str, default="megamovie")
    return parser.parse_args()


def main():
    args  = get_arguments()
    datastore_client = datastore.Client(project=args.project_id)

    query = datastore_client.query(kind=args.photo_table)
    query.add_filter("image_bucket","=", args.image_bucket)
    entities = list(query.fetch())
    images = set()
    for entity in entities:
        images.add(entity.key.name)

    # Instantiates a client
    storage_client = storage.Client()

    # The name for the new bucket
    bucket_name = args.project_id + "-photos"
    bucket = storage_client.get_bucket(bucket_name)
    blobs = bucket.list_blobs()
    blob_sizes = []
    for blob in blobs:
        if blob.name in images:
            blob_sizes.append(blob.size)

    print len(images), sum(blob_sizes)


if __name__ == '__main__':
    main()
