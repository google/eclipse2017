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
from functools import partial
from multiprocessing import Pool
from itertools import compress
import os
import random
import cv2
from gcloud import datastore, storage
from common import config, constants
from common import datastore_schema as ds

HD_MAX_X = 1920
HD_MAX_Y = 1080

def getRescaledDimensions(image, max_w, max_h):
    image_h, image_w = image.shape[:2]
    given_ratio = max_w / float(max_h)
    ratio = image_w / float(image_h)
    if ratio > given_ratio:
        first = max_w
    else:
        first = int(round(ratio * float(max_h)))
    if ratio <= given_ratio:
        second = max_h
    else:
        second = int(round(ratio * float(max_w)))
    return first, second

def get_file_from_gcs(storage_client, fname):
    """
    Download all new files from GCS bucket w/ url <src> to destination folder.
    Must be outside of pipeline class for use as multiprocess map worker
    """
    try:
        blob = storage_client.get_bucket(config.GCS_BUCKET).get_blob(fname)
    except Exception, e:
        msg = 'Failed to download {0} from Cloud Storage.'
        logging.exception(msg.format(fname))
        return False


    if blob:
        fpath = '{0}/{1}'.format(constants.IMAGE_PROCESSOR_DATA_DIR, fname)

        # Get new files only
        if not os.path.isfile(fpath):
            with open(fpath, 'w+') as file_obj:
                try:
                    blob.download_to_file(file_obj)
                    msg = 'Successfully downloaded {0} from GCS'
                    logging.info(msg.format(fname))
                except Exception, e:
                    msg = 'Failed to download {0} from Cloud Storage.'
                    logging.exception(msg.format(fname))
                    return None

        return fname
    else:
        return None

class Pipeline():

    def __init__(self, datastore_client, storage_client):
        self.datastore = datastore_client
        self.storage = storage_client

    def scan(self, entity_kind):
        """
        Scans datastore for all <kind> entities. A list of all
        entity names is returned.
        """

        # Query datastore for all Photo entities, filtering for Photos
        # that are in_gcs=true, and processed=false
        query = self.datastore.query(kind=entity_kind, \
                                     filters=[("in_gcs","=", True),
                                              ("processed","=",False)])

        # Fetch keys only, no need for other entity properties
        query.keys_only()

        # Retrieve all datstore entities. Query currently
        # has no limit & fetches all matching images
        try:
            query = query.fetch()
        except Exception:
            msg = 'Failed to get {0} from Cloud Datastore.'
            logging.exception(msg.format(query))
            return None

        return list(entity.key.name for entity in list(query))

    def process(self, fnames):
        processed_fnames = []
        for fname in fnames:
            local_fname = get_file_from_gcs(self.storage, fname)
            if local_fname == None:
                print "failed to download", fname
                continue
            fpath = '{0}/{1}'.format(constants.IMAGE_PROCESSOR_DATA_DIR, local_fname)


            if fpath.lower().endswith(('.png', '.jpg', '.jpeg')):
                image = cv2.imread(fpath)
                w, h = getRescaledDimensions(image, HD_MAX_X, HD_MAX_Y)
                resized_image = cv2.resize(image, (w, h))
                name, ext = os.path.splitext(local_fname)
                new_fpath = '{0}/{1}{2}'.format(constants.IMAGE_PROCESSOR_DATA_DIR, name, ext)
                cv2.imwrite(new_fpath, resized_image)
                processed_fnames.append(fname)
                msg = 'Successfully processed {0}'
                logging.info(msg.format(fpath))
            else:
                msg = 'Failed to process {0}'
                logging.error(msg.format(fpath))
        return processed_fnames

    def upload(self, fnames):
        uploaded_files = []

        bucket = self.storage.get_bucket(config.GCS_PROCESSED_PHOTOS_BUCKET)
        batch = self.datastore.batch()

        for fname in fnames:
            name, ext = os.path.splitext(fname)
            fpath = '{0}/{1}{2}'.format(constants.IMAGE_PROCESSOR_DATA_DIR, name, ext)
            objname = '{0}{1}'.format(name, ext)
            blob = storage.Blob(objname, bucket)
            try:
                blob.upload_from_file(open(fpath, "rb"))
                uploaded_files.append(fname)
                msg = 'Successfully uploaded {0} to Cloud Storage'
                logging.info(msg.format(fname))
            except Exception, e:
                msg = 'Failed to upload {0} to Cloud Storage: {1}'
                logging.error(msg.format(fname, e))
            else:
                # Update original photo entity
                photo_key = self.datastore.key(ds.DATASTORE_PHOTO, fname)
                photo_entity = self.datastore.get(photo_key)
                photo_entity.update({'processed': True})
                batch.put(photo_entity)

                # Create datastore entry for oriented image
                name, ext = os.path.splitext(fname)
                resized_fname = '{0}{1}'.format(name, ext)
                oriented_key = self.datastore.key(ds.DATASTORE_ORIENTED_IMAGE, resized_fname)
                oriented_entity = datastore.Entity(oriented_key)
                oriented_entity['original_photo'] = photo_key
                oriented_entity['image_type'] = unicode(ds.TOTALITY_IMAGE_TYPE)
                oriented_entity[ds.TOTALITY_ORDERING_PROPERTY] = random.random()
                batch.put(oriented_entity)

        # Cloud Datastore API request
        try:
            batch.commit()
        except Exception, e:
            msg = 'Failed to update Cloud Datastore: {1}'
            logging.error(msg.format(e))

        return uploaded_files
