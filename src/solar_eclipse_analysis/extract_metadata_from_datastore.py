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
import argparse
import pytz
import metadata

DEFAULT_PROJECT = 'eclipse-2017-test'

def get_arguments():
    parser = argparse.ArgumentParser(description='Map image data.')
    parser.add_argument('--project_id', type=str, default=DEFAULT_PROJECT)
    parser.add_argument('--photo_table', type=str, default="Photo")
    parser.add_argument('--output', type=str, default="extracted_metadata.pkl")
    parser.add_argument('--image_bucket', type=str, default="megamovie")
    parser.add_argument('--files', type=str, default="files.txt")
    parser.add_argument('--directory', type=str)
    return parser.parse_args()

def main():
    args  = get_arguments()
    client = datastore.Client(project=args.project_id)

    query = client.query(kind=args.photo_table)
    entities = list(query.fetch())
    results = []
    print "Initial results:", len(entities)
    for entity in entities:
        m = metadata.get_metadata(entity, args.image_bucket, debug=False)
        if m is not None:
            results.append( (entity.key.name, m) )

    print "Filtered results:", len(results)

    f = open(args.files, "wb")
    for result in results:
        f.write("%s/%s\n" % (args.directory, result[0]))
    f.close()
    pickle.dump(dict(results), open(args.output, "wb"))

if __name__ == '__main__':
    main()
