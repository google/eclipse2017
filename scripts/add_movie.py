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

"""Script to add movie to Movie table."""

import datetime
import argparse
from google.cloud import datastore

def get_arguments():
    parser = argparse.ArgumentParser(description='Add movie to Movie table and write to file')
    parser.add_argument('--project_id', type=str, default="eclipse-2017-test-147301")
    parser.add_argument('--id', type=str, default="3syEpviPtjs")
    parser.add_argument('--outfile', type=str, default="static-nginx/app/static/src/movie-id.js")
    return parser.parse_args()

def main():
    args  = get_arguments()
    client = datastore.Client(project=args.project_id)
    key = client.key("Movie")
    entity = datastore.Entity(key = key)
    entity.key = key
    entity.update({'id': args.id,
                   'time': datetime.datetime.utcnow()})
    client.put(entity)
    f = open(args.outfile, "w")
    f.write("var movie_id = '%s';\n" % args.id)
    f.close()

if __name__ == '__main__':
    main()
