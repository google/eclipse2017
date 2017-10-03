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

import exifread
from common.gps import exifread_tags_to_latlon, hms_to_deg, exifread_tags_to_gps_datetime, exifread_tags_to_camera_datetime
def _extract_exif_metadata(fpath):
    """
    Extracts EXIF metadata corresponding to image with fpath
    Returns metadata_dictionary
    """

    metadata = {}
    # convert to exifread support
    f = open(fpath, 'rb')
    try:
        tags = exifread.process_file(f)
    except Exception as e:
        print "exifread failed to process file:", fpath, e
        lat, lon, image_datetime = None, None, None
    else:
        lat, lon = exifread_tags_to_latlon(tags)
        image_datetime = exifread_tags_to_gps_datetime(tags)
        camera_datetime = exifread_tags_to_camera_datetime(tags)
    if image_datetime:
        metadata['image_datetime'] = image_datetime
    if camera_datetime:
        metadata['camera_datetime'] = camera_datetime
    if lat:
        metadata['lat'] = lat
    if lon:
        metadata['lon'] = lon
    return metadata

def _extract_image_metadata(filename, format_, width, height, bucket):
    """
    Extracts image format-specific metadata corresponding to image with fpath
    Returns metadata_dictionary
    """
    metadata = {}
    metadata['image_type'] = unicode(format_)
    metadata['width'] = width
    metadata['height'] = height
    return metadata
