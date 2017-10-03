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

"""Create a collection of locations along and near the eclipse umbral path.

Creates a grid of locations along the eclipse umbral path boundary
(clipped by the US map) and a padded region around it.
"""

import argparse
import numpy as np
import pickle
import sys
from eclipse_gis import eclipse_gis
from shapely.geometry import shape
from shapely.geometry.point import Point
from shapely.geometry.polygon import Polygon
from util import load_map

def get_arguments():
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('--start_datetime', type=str, default='2017/08/21 16:20')
    parser.add_argument('--end_datetime', type=str, default='2017/08/21 19:08')
    # Default to US-map-clipped data
    parser.add_argument('--eclipse_path_data', type=str, default="eclipse_path_data.txt")
    parser.add_argument('--us_map_file', type=str, default="cb_2016_us_nation_20m.shp")
    return parser.parse_args()

def cartesian_product2(arrays):
    """Produce the cartesian product of two arrays."""
    la = len(arrays)
    arr = np.empty([len(a) for a in arrays] + [la])
    for i, a in enumerate(np.ix_(*arrays)):
        arr[...,i] = a
    return arr.reshape(-1, la)

def generate_grid(eclipse_path_data, us_map_polygon, outside=False, umbra_boundary_buffer_size=1.5, x_count=75, y_count=125):
    """Generate a grid of locations within or around the eclipse path.  If
    outside=False, the grid points are within the eclipse path.  If
    outside=True, the grid points are in a buffer region around the
    eclipse path.  umbra_boundary_buffer_size defines the buffer.
    x_count and y_count define the number of points in the grid (the
    full grid covers the bounding box of the United states).
    """
    times, points = eclipse_gis.load_stripped_data(open(eclipse_path_data).readlines())
    boundary, center = eclipse_gis.generate_polygon(points)
    eg = eclipse_gis.EclipseGIS(boundary, center)

    # TODO(dek) use shapely to compute the BB
    min_x = min([item[0] for item in us_map_polygon.exterior.coords])
    min_y = min([item[1] for item in us_map_polygon.exterior.coords])
    max_x = max([item[0] for item in us_map_polygon.exterior.coords])
    max_y = max([item[1] for item in us_map_polygon.exterior.coords])

    # Create a grid of candidate points covering the US
    x_range = np.linspace(min_x, max_x, x_count)
    y_range = np.linspace(min_y, max_y, y_count)
    cp = cartesian_product2([x_range, y_range])
    p = []

    # Create a buffer around the eclipse path bounding
    boundary_buffer = boundary.buffer(umbra_boundary_buffer_size)
    for point in cp:
        Po = Point(point)
        inside_umbra = eg.test_point_within_eclipse_boundary(Po)
        inside_us = us_map_polygon.contains(Po)
        inside_boundary_buffer = boundary_buffer.contains(Po)
        # Filter candidate points
        if not outside and inside_umbra:
            # User wants point inside the eclipse path and point is inside the
            # eclipse path
            p.append(Po)
        elif outside and not inside_umbra and inside_us and inside_boundary_buffer:
            # User wants point outside the eclipse path and point is not inside
            # the eclipse path, is inside the US map boundaries, and inside the boundary buffer
            p.append(Po)

    return p

def main():
    args  = get_arguments()
    us_map = load_map(args.us_map_file)
    # Extract 48 contiguous states
    main_us = us_map.boundary[78:79]
    points = []
    # Convert US map to a shapely Polygon
    for line in main_us.geoms:
        for point in line.coords:
            points.append((point[1], point[0]))
    us_map_polygon = Polygon(points)

    p = generate_grid(args.eclipse_path_data, us_map_polygon, False)

    # Dump inside results
    inside_results = [ (item.x, item.y) for item in p ]
    print "Inside results:", len(inside_results)
    fname = "locations_inside.pkl"
    pickle.dump(inside_results, open(fname, "wb"))

    # Dump outside results
    p = generate_grid(args.eclipse_path_data, us_map_polygon, True)
    outside_results = [ (item.x, item.y) for item in p ]
    print "Outside results:", len(outside_results)
    fname = "locations_outside.pkl"
    pickle.dump(outside_results, open(fname, "wb"))

main()
