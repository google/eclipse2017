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

"""Map image data."""

import logging
import argparse
from google.cloud import datastore, storage
import movie.pipeline
from common import config, constants
from common.chunks import chunks

DEFAULT_PROJECT = 'eclipse-2017-test'

def get_arguments():
    parser = argparse.ArgumentParser(description='Map image data.')
    parser.add_argument('--project_id', type=str, default=DEFAULT_PROJECT)
    return parser.parse_args()

def main():
    logging.basicConfig(level=logging.INFO,
                        format=constants.LOG_FMT_S_THREADED)
    args  = get_arguments()
    datastore_client = datastore.Client(project=args.project_id)
    storage_client = storage.client.Client(project=args.project_id)
    movie_pipeline = movie.pipeline.Pipeline(datastore_client, storage_client)
    fnames = movie_pipeline.scan()
    movie_pipeline.download(fnames)
    print "Rendering %d frames" % len(fnames)
    files_in_movie = movie_pipeline.assemble(fnames)
    print files_in_movie
    movie_pipeline.upload(files_in_movie)

if __name__ == '__main__':
    main()
