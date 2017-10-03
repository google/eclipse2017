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

from datetime import datetime
import logging
import subprocess
from multiprocessing import Pool
from itertools import compress

import os

from google.cloud import datastore, storage
from common import config, constants
from common import datastore_schema as ds
import common.service_account as sa
from common.chunks import chunks

def get_file_from_gcs(fname):
    """
    Download all new files from GCS bucket w/ url <src> to destination folder.
    Must be outside of pipeline class for use as multiprocess map worker
    """
    storage_client = storage.client.Client(project=config.PROJECT_ID, \
                                           credentials=sa.get_credentials())

    fpath = '{0}/{1}'.format(constants.MOVIE_DATA_DIR, fname)
    if os.path.exists(fpath):
        logging.info("Already downloaded file %s" % fpath)
        return True

    try:
        blob = storage_client.get_bucket(config.GCS_PROCESSED_PHOTOS_BUCKET).get_blob(fname)
    except Exception, e:
        msg = 'Failed to download {0} from Cloud Storage.'
        logging.exception(msg.format(fname))
        return False

    if blob:
        # Get files
        with open(fpath, 'w+') as file_obj:
            try:
                blob.download_to_file(file_obj)
                msg = 'Successfully downloaded {0} from GCS'
                logging.info(msg.format(fname))
            except Exception, e:
                msg = 'Failed to download {0} from Cloud Storage.'
                logging.exception(msg.format(fname))
                return False
        return True
    else:
        msg = 'Failed to download blob {0} from Cloud Storage.'
        logging.exception(msg.format(config.GCS_PROCESSED_PHOTOS_BUCKET))
        return False

class Pipeline():

    def __init__(self, datastore_client, storage_client):
        self.prev_fnames = []
        self.datastore = datastore_client
        self.storage = storage_client

    def scan(self):
        """
        Scans datastore for all <kind> entities. A list of all
        entity names is returned.
        """

        # Query datastore for all full disk OrientedImage entities, sorted by the adjusted
        # timestamp of the image (the ordering of the image in the megamovie).
        query = self.datastore.query(kind=ds.DATASTORE_ORIENTED_IMAGE, \
                                     order=[ds.TOTALITY_ORDERING_PROPERTY], \
                                     filters=[("image_type","=", ds.TOTALITY_IMAGE_TYPE)])

        # Fetch keys only, no need for other entity properties
        query.keys_only()

        # Retrieve all datstore entities. Query currently
        # has no limit & fetches all full disk totality images
        try:
            query = query.fetch()
        except Exception:
            msg = 'Failed to get {0} from Cloud Datastore.'
            logging.exception(msg.format(query))
            return None

        fnames = list(entity.key.name for entity in list(query))

        if self.prev_fnames == fnames:
            return []

        self.prev_fnames = fnames

        # Return list of filenames
        return fnames

    def assemble(self, fnames):
        """
        Stitches together movies from an ordered list of filenames.
        Downloads new files from GCS then feeds files to ffmpeg.
        Returns list of files sucessfully stitched into movie & calls stats func
        """

        # Get files from GCS
        pool = Pool(min(len(fnames), constants.MOVIE_DAEMON_MAX_PROCESSES))
        results = pool.map(get_file_from_gcs, fnames)
        pool.terminate()

        # Start ffmpeg subprocess
        ffmpeg_cmd = ["ffmpeg","-y",        # Overwrite exsisting movie file
                    "-f", "image2pipe",
                    "-framerate", constants.MOVIE_FRAMERATE,
                    "-vcodec","mjpeg",
                    "-i", "-",              # Input pipe from stdin
                    "-vf", "scale=1024:-1",
                    "-loglevel", "panic",
                    "-vcodec", "libx264",
                    constants.MOVIE_FPATH]

        ffmpeg_ps = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE)


        fnames = list(compress(fnames, results))
        files_read = self._pipe_to_ffmpeg(ffmpeg_ps, fnames)

        if files_read > constants.MOVIE_MIN_FRAMES:
            ffmpeg_ps.stdin.close()
            ffmpeg_ps.wait()
        else:
            ffmpeg_ps.kill()

        return fnames

    def upload(self, fnames):
        """
        Uploads a list of Movie entities to the datastore and uploads the
        corresponding movie files to Cloud Storage.
        """

        # Name movies based on time created
        movie_dir = datetime.now().strftime("%Y-%m-%d %H:%M")
        movie_name = 'movie-{0}.mp4'.format(movie_dir)

        # Upload movie to Cloud Storage
        bucket = self.storage.get_bucket(config.GCS_MOVIE_BUCKET)
        blob = storage.Blob('{0}/{1}'.format(movie_dir, movie_name), bucket)

        with open(constants.MOVIE_FPATH, 'r') as f:
            try:
                blob.upload_from_file(f)
                msg = 'Successfully uploaded {0} to Cloud Storage'
                logging.info(msg.format(constants.MOVIE_FPATH))
            except Exception, e:
                msg = 'Failed to upload {0} to Cloud Storage: {1}'
                logging.error(msg.format(constants.MOVIE_FPATH, e))
                return False

        if os.path.exists(constants.C_MAP_FPATH):
            map_name = 'map-{0}.png'.format(movie_dir)
            blob = storage.Blob('{0}/{1}'.format(movie_dir, map_name), bucket)

            with open(constants.C_MAP_FPATH, 'r') as c_map:
                try:
                    blob.upload_from_file(c_map)
                    msg = 'Successfully uploaded {0} to Cloud Storage'
                    logging.info(msg.format(map_name))
                except Exception, e:
                    msg = 'Failed to upload {0} to Cloud Storage: {1}'
                    logging.error(msg.format(constants.C_MAP_FPATH, e))

        # Create datastore entry for movie container
        movie_key = self.datastore.key(ds.DATASTORE_MOVIE, movie_name)
        movie_entity = datastore.Entity(movie_key)


        # Store list of composite iamges in movie entity for CC attribution
        photo_keys = list(self.datastore.key(ds.DATASTORE_PHOTO, fname) for fname in fnames)
        movie_entity["composite_photos"] = photo_keys

        try:
            self.datastore.put(movie_entity)
            msg = 'Successfully uploaded {0} to Cloud Datastore'
            logging.info(msg.format(movie_name))
        except Exception, e:
            msg = 'Failed to upload {0} from Cloud Datastore: {1}'
            logging.error(msg.format(movie_name, e))
            return False

        return True

    def _pipe_to_ffmpeg(self, ffmpeg, fnames):
        """
        Write images to stdin of ffmpeg subprocess
        """

        # Track number of files sucessfully passed to ffmpeg
        files_read = 0

        # Pipe files to ffmpeg subprocess
        for fname in fnames:

            fpath = "{0}/{1}".format(constants.MOVIE_DATA_DIR, fname)

            # Read arguement files
            try:
                img = open(fpath, 'r').read()
            except Exception, e:
                msg = 'Failed to write {0}.'
                logging.exception(msg.format(fname))
                continue

            files_read += 1

            # Write to stdin of ffmpeg subprocess
            ffmpeg.stdin.write(img)

        return files_read


def get_file_from_gcs(fname):
    """
    Download all new files from GCS bucket w/ url <src> to destination folder.
    Must be outside of pipeline class for use as multiprocess map worker
    """
    storage_client = storage.client.Client(project=config.PROJECT_ID, \
                                           credentials=sa.get_credentials())

    try:
        blob = storage_client.get_bucket(config.GCS_PROCESSED_PHOTOS_BUCKET).get_blob(fname)
    except Exception, e:
        msg = 'Failed to download {0} from Cloud Storage.'
        logging.exception(msg.format(fname))
        return False

    if blob:
        fpath = '{0}/{1}'.format(constants.MOVIE_DATA_DIR, fname)

        # Get files
        with open(fpath, 'w+') as file_obj:
            try:
                blob.download_to_file(file_obj)
                msg = 'Successfully downloaded {0} from GCS'
                logging.info(msg.format(fname))
            except Exception, e:
                msg = 'Failed to download {0} from Cloud Storage.'
                logging.exception(msg.format(fname))
                return False
        return True
    else:
        msg = 'Failed to download blob {0} from Cloud Storage.'
        logging.exception(msg.format(config.GCS_PROCESSED_PHOTOS_BUCKET))
        return False
