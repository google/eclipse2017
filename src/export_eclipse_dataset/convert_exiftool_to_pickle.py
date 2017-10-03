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

"""Convert output from exiftool to pickle format."""
import os
import glob
import argparse
import cPickle as pickle

def get_arguments():
    parser = argparse.ArgumentParser(description="Convert output from exiftool to pickle format.")
    parser.add_argument('--exif_directory', type=str, default="exif")
    parser.add_argument('--exif_output', type=str, default="exiftool.pkl")
    parser.add_argument('--filtered_photo_metadata', type=str, default="filtered_photo_metadata.pkl")
    parser.add_argument('--directory', type=str, default="photos")
    parser.add_argument('--output_directory', type=str, default="photos-exif-stripped")
    return parser.parse_args()

# Parse a section field that looks like [ExifIFD]      ApertureValue:   5
# into d['ExifIFD']['ApertureValue'] = 5
def parse_section_field(lines):
    d = {}
    for line in lines:
        x = line.split("]")
        section = x[0][1:]
        if section not in d:
            d[section] = {}
        y = x[1].split(":")
        key = y[0].strip()
        value = y[1].strip()
        d[section][key] = value
    return d

def main():
    args  = get_arguments()

    filtered_photo_metadata = pickle.load(open(args.filtered_photo_metadata))

    include_photos = []
    for photo in filtered_photo_metadata:
        key = photo.key.name
        f = os.path.join(args.directory, key)
        f2 = os.path.join(args.output_directory, key)
        if not os.path.exists(f):
            print "missing", f
            continue
        include_photos.append(key)

    d = {}
    for photo in include_photos:
        file_ = os.path.join(args.exif_directory, photo + ".exif.txt")
        i = open(file_).readlines()
        d[photo] = parse_section_field(i)
    pickle.dump(d, open(args.exif_output, "wb"))

if __name__ == '__main__':
    main()
