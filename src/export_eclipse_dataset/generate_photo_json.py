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
import argparse
import datetime
from google.cloud import datastore
import cPickle as pickle
import json
import csv

"""Convert Photo records to JSON"""

DEFAULT_PROJECT="eclipse-2017-test"
GCS_URI = 'https://storage.googleapis.com/gcs-public-data--eclipse-megamovie/v0.1'

def get_arguments():
    parser = argparse.ArgumentParser(description='Convert Photo records to JSON')
    parser.add_argument('--filtered_photo_metadata', type=str, default="filtered_photo_metadata.pkl")
    parser.add_argument('--user_random_uuid', type=str, default="user_random_uuid.pkl")
    parser.add_argument('--exif_output', type=str, default="exiftool.pkl")
    parser.add_argument('--json_output', type=str, default="photos.json")
    parser.add_argument('--detected_circles', type=str, default="detected_circles.pkl")
    parser.add_argument('--vision_labels', type=str, default="vision_labels.pkl")
    parser.add_argument('--states', type=str, default="states.pkl")
    parser.add_argument('--totality', type=str, default="totality.pkl")
    parser.add_argument('--make_model_mobile', type=str, default="make_model_mobile.csv")
    return parser.parse_args()


def datetime_serialize(obj):
    if isinstance(obj, datetime.datetime):
        return obj.strftime('%Y-%m-%dT%H:%M:%S.%f')

# Reliably extracting dimensions from EXIF is hard.
def get_dimensions(key, e):
    if e.has_key('ExifIFD'):
        exififd = e['ExifIFD']
        if exififd.has_key('ExifImageHeight') and exififd.has_key('ExifImageWidth'):
            height = exififd['ExifImageHeight']
            width = exififd['ExifImageWidth']
            return width, height
        else:
            if e.has_key('SubIFD'):
                subifd = e['SubIFD']
                if subifd.has_key('ImageHeight'):
                    height = subifd['ImageHeight']
                    width = subifd['ImageWidth']
                    return width, height
            if e.has_key('SubIFD1'):
                subifd1 = e['SubIFD1']
                if subifd1.has_key('ImageHeight'):
                    height = subifd1['ImageHeight']
                    width = subifd1['ImageWidth']
                    return width, height

            file_ = e['File']
            if file_.has_key('ImageHeight'):
                height = file_['ImageHeight']
                width = file_['ImageWidth']
                return width, height
    if e.has_key('IFD0'):
        ifd0 = e['IFD0']
        height = ifd0['ImageHeight']
        width = ifd0['ImageWidth']
        return width, height

    print "Failed to process", key
    return None, None


def main():
    args  = get_arguments()

    filtered_photo_metadata = pickle.load(open(args.filtered_photo_metadata, "rb"))
    user_random_uuid = pickle.load(open(args.user_random_uuid, "rb"))
    detected_circles = pickle.load(open(args.detected_circles, "rb"))
    vision_labels = pickle.load(open(args.vision_labels, "rb"))
    exif = pickle.load(open(args.exif_output, "rb"))
    states = pickle.load(open(args.states, "rb"))
    totality = pickle.load(open(args.totality, "rb"))

    reader = csv.reader(open(args.make_model_mobile, 'rb'), delimiter='|')
    make_model_is_mobile = set()
    rows = list([ row for row in reader ])
    for row in rows[1:]:
        if row[2] == 'True':
            make_model_is_mobile.add(tuple(row[:2]))

    f = open(args.json_output, "w")
    for photo in filtered_photo_metadata:
        key = photo.key.name
        e = exif[key]
        file_type = e['File']['FileType']
        if e.has_key('ExifIFD'):
            exposure_time = e['ExifIFD'].get('ExposureTime', None)
            aperture_value = e['ExifIFD'].get('ApertureValue', None)
        else:
            exposure_time = None
            aperture_value = None
        if e.has_key('IFD0'):
            make = e['IFD0'].get('Make', None)
            model = e['IFD0'].get('Model', None)
        else:
            make = None
            model = None

        if (make, model) in make_model_is_mobile:
            is_mobile = True
        else:
            is_mobile = False

        if key in detected_circles:
            x = detected_circles[key]
            if x is None:
                detected_circle = None
            else:
                dc = map(float, list(x[0][0]))
                detected_circle = {
                    'center_x': dc[0],
                    'center_y': dc[1],
                    'radius': dc[2]
                    }
        else:
            detected_circle = None

        extension = e['File']['FileTypeExtension']
        storage_uri = os.path.join(GCS_URI, key + "." + extension)

        state = states.get(key, None)
        is_totality = totality.get(key, None)
        
        width, height = get_dimensions(key, e)
        vl = vision_labels.get(key, None)
        if vl is not None:
            vls = ','.join(vl)
        else:
            vls = ''
        # Output JSON record with denormalized photo metadata.
        record = {
            'id': key,
            'camera_datetime': photo.get('camera_datetime', None),
            'uploaded_date': photo['uploaded_date'],
            'image_datetime': photo['image_datetime'],
            'lat': photo['lat'],
            'lon': -photo['lon'],
            'image_bucket': photo['image_bucket'],
            'image_type': file_type,
            'equatorial_mount': photo['equatorial_mount'],
            'datetime_repaired': photo.get('datetime_repaired', False),
            'upload_session_id': photo['upload_session_id'],
            'user': user_random_uuid[photo['user'].name],
            'width': int(width),
            'height': int(height),
            'make': make,
            'model': model,
            'exposure_time': exposure_time,
            'aperture_value': aperture_value,
            'detected_circle': detected_circle,
            'storage_uri': storage_uri,
            'state': state,
            'totality': is_totality,
            'is_mobile': is_mobile,
            'vision_labels': vls,
            }
        json.dump(record, f, default=datetime_serialize)
        f.write("\n")
    f.close()



if __name__ == '__main__':
    main()
