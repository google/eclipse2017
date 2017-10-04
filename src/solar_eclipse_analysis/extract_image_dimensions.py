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
import libraw

TMPDIR=os.getenv("TMPDIR")

def get_arguments():
    parser = argparse.ArgumentParser(description='Read images.')
    parser.add_argument('--files', type=str, default="files.txt")
    parser.add_argument('--output', type=str, default="image_dims.pkl")
    return parser.parse_args()

def process_image(filename):
    fpath = os.path.basename(filename)
    try:
        img = Image.open(filename)
    except IOError as e:
        if e.message.startswith("cannot identify image file"):
            tiff_output_file = os.path.join(TMPDIR, fpath + ".tiff")
            if not os.path.exists(tiff_output_file):
                print "error: cached tiff for", fpath, "does not exist at", tiff_output_file
                return fpath, None
            try:
                img = Image.open(tiff_output_file)
            except IOError as e3:
                print "Failed to open cached tiff", fpath, str(e3)
                return fpath, None
        else:
            print "IOError opening", filename, e
            return fpath, None

    format_ = img.format
    width = img.width
    height = img.height
    if width == 160:
        try:
            r = Raw(filename)
        except libraw.errors.FileUnsupported:
            print "libraw failed to read:", filename
            return fpath, None
        width = r.metadata.width
        height = r.metadata.height
        format_ = "tiff_raw"
    return filename, (format_, width, height)

def main():
    args  = get_arguments()
    items = [line.strip() for line in open(args.files).readlines()]
    items.sort()

    # for item in items:
    #     process_image(item)

    p = Pool(20)
    results = p.map(process_image, items)
    f = open(args.output, "wb")
    pickle.dump(results, f)
    f.close()

if __name__ == '__main__':
    main()
