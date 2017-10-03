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
from google.cloud import datastore, storage
from common import config, constants
from common import datastore_schema as ds
from common.find_circles import findCircles
import numpy as np
from eclipse_gis import eclipse_gis
from shapely.geometry import Point

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

        times, points = eclipse_gis.load_stripped_data(open("/app/data/eclipse_data.txt").readlines())
        boundary, center_line = eclipse_gis.generate_polygon(points)
        self.eclipse_gis = eclipse_gis.EclipseGIS(boundary, center_line)

    def scan(self, entity_kind):
        """
        Scans datastore for all <kind> entities. A list of all
        entity names is returned.
        """

        # Query datastore for all Photo entities, filtering for Photos
        # that are in_gcs=true, and processed=false
        query = self.datastore.query(kind=entity_kind, \
                                     filters=[("in_gcs","=", True),
                                              ("confirmed_by_user","=",True),
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
            try:
                local_fname = get_file_from_gcs(self.storage, fname)
            except Exception as e:
                logging.error("Failed to download: %s" % fname)
                continue
            if local_fname == None:
                logging.error("Failed to download: %s" % fname)
                continue
            fpath = '{0}/{1}'.format(constants.IMAGE_PROCESSOR_DATA_DIR, local_fname)

            image = cv2.imread(fpath)
            result = findCircles(image)
            if result is not None:
                cx, cy, r = result
                image_cols, image_rows, _ = image.shape
                if cx - r >= 0 and cx + r < image_rows and cy - r >= 0 and cy + r < image_cols:
                    center_y = image_cols / 2
                    center_x = image_rows / 2
                    dx = (center_x-cx)
                    dy = (center_y-cy)
                    M = np.float32([[1,0,dx],[0,1,dy]])
                    # Translate center of sun to center of image
                    image = cv2.warpAffine(image,M,(image_rows,image_cols))
                    image_cols, image_rows, _ = image.shape
                    ratio = 100. / r
                    first = int(round(image_cols * ratio))
                    second = int(round(image_rows * ratio))
                    # Scale image so sun is 100 pixels
                    image = cv2.resize(image, (second, first))
                    if image_rows > second and image_cols > first:
                        border_x = int(round((image_rows - second)/2.))
                        border_y = int(round((image_cols - first)/2.))
                        image = cv2.copyMakeBorder(image, border_y, border_y,
                                                   border_x, border_x,
                                                   cv2.BORDER_CONSTANT, value=[0,0,0])
                    elif image_rows < second and image_cols < first:
                        border_x = int(round((second - image_rows)/2.))
                        border_y = int(round((first - image_cols)/2.))
                        image = image[border_y:first-border_y, border_x:second-border_x]
                    else:
                        logging.error("Unsupported: %s" % str((image_rows, second, image_cols, first)))
                        raise RuntimeError
                    name, ext = os.path.splitext(local_fname)
                    new_fpath = '{0}/{1}{2}'.format(constants.IMAGE_PROCESSOR_DATA_DIR, name, ext)
                    cv2.imwrite(new_fpath + ".jpeg", image)
                    os.rename(new_fpath + ".jpeg", fpath)
                    processed_fnames.append(fname)
                    logging.info('Successfully processed {0}'.format(fpath))
                else:
                    logging.info("Unsuccessfully processed {0}: eclipse clipped by edge".format(fpath))
            else:
              logging.info("Unsuccessfully processed {0}: no eclipse circle found")
        return processed_fnames

    def upload(self, fnames):
        uploaded_files = []

        bucket = self.storage.get_bucket(config.GCS_PROCESSED_PHOTOS_BUCKET)
        batch = self.datastore.batch()
        batch.begin()

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
                lat = photo_entity['lat']
                lon = photo_entity['lon']
                # TODO(dek): properly repsect LatRef and LonRef here
                lon = -lon
                p = Point(lat, lon)
                np = self.eclipse_gis.interpolate_nearest_point_on_line(p)
                # TODO(dek):
                # map each location into its associated center point
                # (based on the golden data in eclipse_gis)
                # and sort by location/time bins
                oriented_entity[ds.TOTALITY_ORDERING_PROPERTY] = np
                batch.put(oriented_entity)

        # Cloud Datastore API request
        try:
            batch.commit()
        except Exception, e:
            msg = 'Failed to update Cloud Datastore: {1}'
            logging.error(msg.format(e))

        return uploaded_files
