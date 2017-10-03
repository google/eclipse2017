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

import logging
import time
import os

from google.cloud import datastore, storage

from common import config, constants
from common import datastore_schema as ds
import common.service_account as sa

import pipeline
import pipeline_stats

# Used when running locally
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = constants.SERVICE_ACCOUNT_PATH

def main(sleep_time=constants.MOVIE_DAEMON_SLEEP_TIME_S):

    logging.basicConfig(level=logging.INFO,
                        format=constants.LOG_FMT_S_THREADED)
    logging.info("Reading images from gs://" + config.GCS_PROCESSED_PHOTOS_BUCKET)
    logging.info("Writing movies to gs://" + config.GCS_MOVIE_BUCKET)

    #Get current projects storage and datastore client
    credentials = sa.get_credentials()
    datastore_client = datastore.Client(project=config.PROJECT_ID, \
                                        credentials=credentials)

    storage_client = storage.client.Client(project=config.PROJECT_ID, \
                                           credentials=credentials)

    # Create new instance of movie pipeline w/ datastore & GCS
    movie_pipeline = pipeline.Pipeline(datastore_client, storage_client)
    movie_stats = pipeline_stats.Pipeline_Stats(datastore_client, storage_client)

    while True:

        # Get all newly pre-processed images
        fnames = movie_pipeline.scan()

        # Stitch new images into new/exsisting megamovie(s)
        if fnames:
            # Seperate files based on clusters of photos
            clusters = movie_stats.get_clusters(fnames)

            # Concatenates frames into movies and stores in constants.MOVIE_DATA_DIR
            files_in_movie = movie_pipeline.assemble(fnames)

            # Upload movie file(s)
            if files_in_movie:
                movie_pipeline.upload(files_in_movie)

        # Allow files to accumulate before taking our next pass
        time.sleep(sleep_time)

if __name__ == '__main__':
    main()
