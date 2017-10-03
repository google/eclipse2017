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
from google.cloud import datastore
import cPickle as pickle
import json
import shlex

DEFAULT_PROJECT="eclipse-2017-test"
def get_arguments():
    parser = argparse.ArgumentParser(description='Render movie.')
    parser.add_argument('--user_metadata', type=str, default="user_metadata.pkl")
    parser.add_argument('--user_random_uuid', type=str, default="user_random_uuid.pkl")
    parser.add_argument('--json_output', type=str, default="photos.json")
    parser.add_argument('--image_dir', type=str, default="images")
    parser.add_argument('--output_image_dir', type=str, default="output_images")
    parser.add_argument('--rename_credits', type=str, default="rename_credits.txt")
    parser.add_argument('--exif_output', type=str, default="exiftool.pkl")
    parser.add_argument('--filtered_photo_metadata', type=str, default="filtered_photo_metadata.pkl")
    return parser.parse_args()

def chunks(list_, num_items):
    """break list_ into n-sized chunks..."""
    results = []
    for i in range(0, len(list_), num_items):
        results.append(list_[i:i+num_items])
    return results

def cleanup_name(rename, name):
    if name in rename:
        name = rename[name]
    if '@' in name:
        name = name.split("@")[0]
    name = name.replace("&amp;", "&")
    return name

def main():
    args  = get_arguments()
    # Convert user metadata to dictionary keyed by user ID
    user_metadata = pickle.load(open(args.user_metadata, "rb"))
    user_metadata = dict([ (item.key.name, item) for item in user_metadata])
    filtered_photo_metadata = pickle.load(open(args.filtered_photo_metadata, "rb"))
    user_random_uuid = pickle.load(open(args.user_random_uuid, "rb"))
    photo_data = dict([ (photo.key.name, photo) for photo in filtered_photo_metadata ])
    exif = pickle.load(open(args.exif_output, "rb"))

    rename = {}
    if not os.path.exists(args.rename_credits):
        rename_credits = open(args.rename_credits).readlines()
        for line in rename_credits:
          s = line.split('\t')
          rename[s[0]] = s[1].strip()

    # Load the photo JSON data
    s = '[' + ",".join(open(args.json_output, "rb").readlines()) + ']'
    photos = json.loads(s)

    # Iterate over all the photos we are exporting.
    for photo in photos:
        id_ = photo['id']
        e = exif[id_]
        if e.has_key('GPS'):
            if e['GPS'].has_key('GPSLatitude'):
                exif_lat = float(e['GPS']['GPSLatitude'])
            else:
                exif_lat = None
            if e['GPS'].has_key('GPSLongitude'):
                exif_lon = -float(e['GPS']['GPSLongitude'])
            else:
                exif_lon = None
            if e['GPS'].has_key('GPSDateStamp'):
                exif_datestamp = e['GPS']['GPSDateStamp']
            else:
                exif_datestamp = None
            if e['GPS'].has_key('GPSTimeStamp'):
                exif_timestamp = e['GPS']['GPSTimeStamp']
            else:
                exif_timestamp = None
        else:
            exif_lat = None
            exif_lon = None
            exif_datestamp = None
            exif_timestamp = None

        m = photo_data[id_]
        db_lat = m['lat']
        db_lon = -m['lon']
        image_datetime = m['image_datetime']
        anonymous_photo = m['anonymous_photo']
        add_exif_lat = False
        add_exif_lon = False
        add_exif_datestamp = False
        add_exif_timestamp = False
        if exif_lat is None:
            add_exif_lat = True
        if exif_lon is None:
            add_exif_lon = True
        if exif_datestamp is None:
            add_exif_datestamp = True
        if exif_timestamp is None:
            add_exif_timestamp = True

        # Apply per-image fixups
        extra = []
        if add_exif_lon:
            extra.append("-GPSLongitudeRef=W -GPSLongitude=%f" % -db_lon)
        if add_exif_lat:
            extra.append("-GPSLatitudeRef=N -GPSLatitude=%f" % db_lat)
        if add_exif_datestamp:
            extra.append("-GPSDateStamp=%s" % image_datetime.strftime("%Y:%m:%d"))
        if add_exif_timestamp:
            extra.append("-GPSTimeStamp=%s" % image_datetime.strftime("%H:%S:%S"))

        if anonymous_photo:
            extra.append("-Artist=\"Anonymous Photographer\"")
        else:
            user_id = m['user'].name
            md = user_metadata[user_id]
            name = cleanup_name(rename, md['name'])
            name = name.encode('utf-8').replace("(", "\\(").replace(")", "\\)")
            extra.append("-Artist=\"" + name + "\"")

        extra.append("-License=\"CC0 1.0 (Public Domain Dedication)\"")
        extra.append("-Copyright=\"CC0 1.0 (Public Domain Dedication)\"")

        extra_flags = " ".join(extra)
        ofile = os.path.join(args.output_image_dir, id_)
        ifile = os.path.join(args.image_dir, id_)
        extension = e['File']['FileTypeExtension']
        print "exiftool -@ flagsFile %s -o %s %s && mv %s %s" % (
            extra_flags, str(ofile), str(ifile), str(ofile), str(ofile) + "." + extension)

        # Known problems:
        # photos whose ApertureValue=inf does not round-trip properly: derived images have ApertureValue missing

if __name__ == '__main__':
    main()
