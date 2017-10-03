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

"""Analyze image (debug tool)."""

import logging
import argparse
from common.exif import _extract_exif_metadata, _extract_image_metadata
from PIL import Image
from rawkit.raw import Raw

def get_arguments():
    parser = argparse.ArgumentParser(description='Analyze photo.')
    parser.add_argument('--filename', type=str)
    return parser.parse_args()

def main():
    args  = get_arguments()
    metadata = _extract_exif_metadata(args.filename)
    print "EXIF metadata:", metadata
    try:
        img = Image.open(args.filename)
        format_ = img.format
        if format_  == 'TIFF':
            output_file = "/tmp/" + filename + ".jpg"
            img.save(output_file)
    except IOError as e:
        try:
            with Raw(filename=fpath) as raw:
                tiff_output_file = "/tmp/" + filename + ".tiff"
                raw.save(filename=tiff_output_file)
        except Exception as e:
            logging.exception("Failed to parse file with PIL or rawkit: %s" % fpath)
            return False, fpath
        jpg_output_file = "/tmp/" + filename + ".jpg"
        img = Image.open(tiff_output_file)
        img.save(jpg_output_file)
        format_ = 'raw'

    print "Format:", format_
    width = img.width
    height = img.height
    metadata = _extract_image_metadata(args.filename, format_, width, height, None)
    print "Width:", width
    print "Height:", height
    print "Image metadata:", metadata

if __name__ == '__main__':
    main()
