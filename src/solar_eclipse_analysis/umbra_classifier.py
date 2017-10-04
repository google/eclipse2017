import shutil
import os
import datetime
import shapefile
import argparse
import pickle
from shapely.geometry import Polygon, Point, LineString

from shapely.geometry import shape
from multiprocessing import Pool
import functools

def get_arguments():
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('--input', type=str, default="extracted_metadata.pkl")
    parser.add_argument('--umbra_polys', type=str, default='umbra_polys.pkl')
    parser.add_argument('--umbra_photos', type=str, default='umbra_photos.pkl')
    parser.add_argument('--photo_selections', type=str, default='photo_selections.pkl')
    parser.add_argument('--directory', type=str, default="classify")
    parser.add_argument('--selected_directory', type=str, default="selected")
    parser.add_argument('--image_directory', type=str)
    return parser.parse_args()

def main():
    args = get_arguments()
    # Load table of umbra to photo mappings
    umbra_photos = pickle.load(open(args.umbra_photos))
    polys = pickle.load(open(args.umbra_polys))

    for i, poly in enumerate(polys):
        dirname = os.path.join(args.directory, str(i))
        if not os.path.exists(dirname):
            os.mkdir(dirname)

    # Load photo points
    r = pickle.load(open(args.input))

    prevset = set()
    k = umbra_photos.keys()
    k.sort()
    selections = {}
    for umbra_photo in k:
        items = umbra_photos[umbra_photo]
        if len(items):
            dirname = os.path.join(args.directory, str(umbra_photo))
            new = []
            for item in items:
                ni = list(item[:])
                fname = item[1]
                if 'width' not in r[fname]:
                    continue
                if 'height' not in r[fname]:
                    continue
                width = r[fname]['width']
                height = r[fname]['height']
                ni.append(width)
                ni.append(height)
                new.append(ni)
            selections[umbra_photo] = new

    pickle.dump(selections, open(args.photo_selections, "wb"))

if __name__ == '__main__':
    main()
