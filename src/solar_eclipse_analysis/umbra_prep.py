import os
import datetime
import shapefile
import argparse
import pickle
from shapely.geometry import Polygon, Point, LineString

from shapely.geometry import shape

def get_arguments():
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('--umbra', type=str, default='data/w_umbra17_1m.shp')
    parser.add_argument('--umbra_output', type=str, default='umbra_polys.pkl')
    parser.add_argument('--us_map_file', type=str, default="data/cb_2016_us_nation_20m.shp")
    return parser.parse_args()

def load_map(map_path):
    sh = shapefile.Reader(map_path)
    feature = sh.shapeRecords()[0]
    first = feature.shape.__geo_interface__
    shp_geom = shape(first)
    return shp_geom

def f(args):
    poly, poly_centroid, i, point, j = args
    if poly.contains(point):
        d = poly_centroid.distance(point)
        return (i, j), d

def main():
    args = get_arguments()

    us_map = load_map(args.us_map_file)
    # Extract 48 contiguous states
    main_us = us_map.boundary[78:79]
    points = []
    # Convert US map to a shapely Polygon
    for line in main_us.geoms:
        for point in line.coords:
            points.append((point[0], point[1]))
    us_map_polygon = Polygon(points)


    umbra_shape = shapefile.Reader("data/umbra17_1s.shp")
    # extract umbra polygons and their attributes (UTC time)

    # Generate sequence of all umbra polygons across the US.  Only include umbra
    # polygons if they intersect with the US map

    shapes = umbra_shape.shapes()
    records = umbra_shape.shapeRecords()
    assert(len(shapes) == len(records))
    polys = []
    for i, shape in enumerate(shapes):
        record = records[i].record
        poly = Polygon(shape.points)
        dt = datetime.datetime.strptime("2017/08/21 " + record[0], "%Y/%m/%d %H:%M:%S")
        if us_map_polygon.intersects(poly):
            polys.append( (poly, poly.centroid, dt) )
    with open(args.umbra_output, "wb") as o:
        pickle.dump(polys, o)

if __name__ == '__main__':
    main()
