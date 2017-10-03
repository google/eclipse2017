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

import logging
from common.gps import apply_timezone_offset

def partition_gps(entities):
    """Partition Photo entities by GPS lat/lon and datetime.
    Arguments:
      entities: sequence of Photo entities

    Returns
      complete_images: sequence of Photos containing both GPS lat/lon and datetime
      incomplete_images: sequence of Photos that do not contain both GPS lat/lon and datetime
    """
    complete_images = []
    incomplete_images = []
    for entity in entities:
        has_lat = entity.has_key('lat')
        has_lon = entity.has_key('lon')
        has_datetime = entity.has_key('image_datetime')
        if has_lat and has_lon and has_datetime:
            complete_images.append(entity)
        else:
            incomplete_images.append(entity)

    return complete_images, incomplete_images

def update_incomplete(complete_image, incomplete_image):
    """Update incomplete photos based on complete photo.  Only the lat/lon
       are updated, not the datetime, since the datetime of the
       complete photo is not relevant (the incomplete photo's camera
       timestamp is used instead of GPS)
    Arguments:
      complete_image: a photo entity with GPS lat/lon and datetime
      incomplete_image: a photo entity lacking GPS lat/lon and datetime
    returns:
      The updated incomplete photo entity, which is now complete
    """
    if not incomplete_image.has_key('lat') and complete_image is not None:
        incomplete_image['lat'] = complete_image['lat']
    if not incomplete_image.has_key('lon') and complete_image is not None:
        incomplete_image['lon'] = complete_image['lon']
    if not incomplete_image.has_key('image_datetime') and incomplete_image.has_key('camera_datetime'):
        logging.info("Repairing image_datetime from camera_datetime")
        if incomplete_image.has_key('lon') and incomplete_image.has_key('lat'):
            incomplete_image['image_datetime'] = apply_timezone_offset(incomplete_image['lat'], -incomplete_image['lon'], incomplete_image['camera_datetime'])
            incomplete_image['datetime_repaired'] = True

    return incomplete_image
