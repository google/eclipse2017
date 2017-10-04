"""Read images"""

import os
import logging
import argparse
import pickle
from exif import _extract_exif_metadata, _extract_image_metadata
from PIL import Image
from rawkit.raw import Raw
from multiprocessing import Pool
from functools import partial

IMGDIR=os.getenv("IMAGE_DIR")


def get_arguments():
    parser = argparse.ArgumentParser(description='Read images.')
    parser.add_argument('--input', type=str, default="extracted_metadata.pkl")
    parser.add_argument('--files', type=str)
    return parser.parse_args()

def process_image(d filename):
    img = Image.open(filename)
    format_ = img.format
    width = img.width
    height = img.height
    return filename, (format_, width, height)

def main():
    args  = get_arguments()
    r = pickle.load(open(args.input))
    for key in r:
        s = r[key]
        if s.has_key('width') and s.has_key('height'):
            width, height = s['width'], s['height']
        else:
            width, height = None
        process_image(r, os.path.join(IMGDIR, key))
if __name__ == '__main__':
    main()
