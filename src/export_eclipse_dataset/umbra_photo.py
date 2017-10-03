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
    parser.add_argument('--filtered_photo_metadata', type=str, default="filtered_photo_metadata.pkl")
    parser.add_argument('--umbra_polys', type=str, default='umbra_polys.pkl')
    parser.add_argument('--umbra_photos', type=str, default='umbra_photos.pkl')
    parser.add_argument('--totality_output', type=str, default='totality.pkl')
    return parser.parse_args()

def load_map(map_path):
    sh = shapefile.Reader(map_path)
    feature = sh.shapeRecords()[0]
    first = feature.shape.__geo_interface__
    shp_geom = shape(first)
    return shp_geom


def process_item(d, poly_dts):
    key = d.key.name
    lat = d['lat']
    lon = -d['lon']
    dt = d['image_datetime']
    point = Point(lon, lat)
    # # Based on photo's time, find the umbra whose center point's time is the same
    # TODO(dek): fix https://b.corp.google.com/issues/64974121
    pdt = dt.replace(tzinfo=None)
    if pdt not in poly_dts:
        print "Point outside eclipse time window:", key, pdt, lat, lon
        return key, False
    current_poly = poly_dts[pdt][0]
    if not current_poly.contains(point):
        print "Point outside eclipse time window:", key, pdt, lat,lon
        return key, False
    # Now we know this photo point/dt is in totality
    return key, True

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
    r = pickle.load(open(args.filtered_photo_metadata))

    # photo_fname = {}
    # fnames = []

    # for i, fname in enumerate(r):
    #     fnames.append(fname)
    # fnames.sort()

    results = []
    for item in r:
        result = process_item(item, poly_dts)
        results.append(result)
    pickle.dump(dict(results), open(args.totality_output, "wb"))

if __name__ == '__main__':
    main()
