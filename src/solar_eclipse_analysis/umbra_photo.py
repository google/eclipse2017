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
    return parser.parse_args()

def load_map(map_path):
    sh = shapefile.Reader(map_path)
    feature = sh.shapeRecords()[0]
    first = feature.shape.__geo_interface__
    shp_geom = shape(first)
    return shp_geom


def process_item(d, fname, polys, poly_dts):
    lat = d['lat']
    lon = -d['lon']
    dt = d['image_datetime']
    point = Point(lon, lat)
    # # Based on photo's time, find the umbra whose center point's time is the same
    # TODO(dek): fix https://b.corp.google.com/issues/64974121
    pdt = dt.replace(tzinfo=None)
    if pdt not in poly_dts:
        print "Point outside eclipse time window:", fname, pdt, lat, lon
        return None
    current_poly = poly_dts[pdt][0]
    if not current_poly.contains(point):
        print "Point outside eclipse time window:", fname, pdt, lat,lon
        return None
    # Now we know this photo point/dt is in totality
    # Find all umbra polys that contain this photo
    x = []
    for j, p in enumerate(polys):
        poly, poly_centroid, poly_dt = p
        if poly.contains(point):
            x.append((j, (poly_centroid.distance(point), fname, lat, lon, dt)))
    return x

def main():
    args = get_arguments()

    polys = pickle.load(open(args.umbra_polys))
    poly_table = {}
    for j, poly in enumerate(polys):
        poly_table[j] = []

    poly_dts = {}
    for poly, poly_centroid, poly_dt in polys:
        poly_dts[poly_dt] = poly, poly_centroid

    # Load photo points
    r = pickle.load(open(args.input))

    photo_fname = {}
    included_photos = set()
    fnames = []
    for i, fname in enumerate(r):
        fnames.append(fname)
    fnames.sort()
    
    for i, fname in enumerate(fnames):
        d = r[fname]
        results = process_item(d, fname, polys, poly_dts)
        if results is None:
            # print "Photo", i, "failed to process item"
            continue
        # print "Photo", i, "successfully process item"
        for result in results:
            j, data = result
            poly_table[j].append(data)


    # Sort by distance of photo to center of enclosing umbra
    for j in poly_table:
        poly_table[j].sort()
    pickle.dump(poly_table, open(args.umbra_photos, "wb"))

if __name__ == '__main__':
    main()
