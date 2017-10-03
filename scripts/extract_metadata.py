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

"""Extract metadata from image."""

import argparse
import exifread
from PIL import Image
from common.gps import exifread_tags_to_latlon, hms_to_deg, exifread_tags_to_gps_datetime, exifread_tags_to_camera_datetime, apply_timezone_offset
from common.geometry import ratio_to_decimal

def get_arguments():
    parser = argparse.ArgumentParser(description='Extract metadata from image')
    parser.add_argument('--filename', type=str)
    return parser.parse_args()

def main():
    args  = get_arguments()
    f = open(args.filename, 'rb')
    tags = exifread.process_file(f)
    lat, lon = exifread_tags_to_latlon(tags)
    image_datetime = exifread_tags_to_gps_datetime(tags)
    camera_datetime = exifread_tags_to_camera_datetime(tags)
    if lat is not None and lon is not None and camera_datetime is not None:
        camera_datetime = apply_timezone_offset(lat, -lon, camera_datetime)
        print lat, -lon, image_datetime, camera_datetime

if __name__ == '__main__':
    main()
