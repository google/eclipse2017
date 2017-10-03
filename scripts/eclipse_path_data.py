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

"""Generate canonical US-map-clipped eclipse path data from full path data.

Starting from official NASA Eclipse Path Data
(https://eclipse.gsfc.nasa.gov/SEpath/SEpath2001/SE2017Aug21Tpath.html),
parse the data, and clip the resulting map locations by the US map
boundaries.

The clipped path is used to filter images by their GPS coordinates,
define a logical coordinate representing the center of the umbral path
(for ordering spatially distinct photos), and generating faux
eclipse renderings within and outside the umbral path.
The file containing official NASA eclipse path data can downloaded from here:
    https://eclipse.gsfc.nasa.gov/SEpath/SEpath2001/SE2017Aug21Tpath.html
The file containing official US map cartographic boundaries can be downloaded from here:
    https://catalog.data.gov/dataset/2016-cartographic-boundary-file-united-states-1-20000000
"""

import argparse
import ephem
import math
import time
from BeautifulSoup import BeautifulSoup
from shapely.geometry import LineString, Point, Polygon, shape
from map_util import parse_html, load_map, us_shape_to_points

def get_arguments():
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('--eclipse_path_html', type=str, default='SE2017Aug21Tpath.html')
    parser.add_argument('--eclipse_path_output', type=str, default='eclipse_path_data.txt')
    parser.add_argument('--us_map_file', type=str, default="cb_2016_us_nation_20m.shp")
    return parser.parse_args()

def fmt_loc(loc):
    b, a = math.modf(abs(loc))
    s = "%3s %04.1f" % (int(a), b*60.)
    return s

def fmt_loc_pair(loc_pair):
    return fmt_loc(loc_pair[0]), fmt_loc(loc_pair[1])


def interpolate_time(cut_point, center_linestring, times):
    """Interpolate the time corresponding to cut_point along center_linestring.

    times and center_linestring are arrays of the same length,
    corresponding to eclipse totality times and locations in sequence
    across the country.

    cut_point is a point along the lines formed by adjacent points in center_linestring.

    This function returns the time corresponding to the cut point, by
    linearly interpolating the point along time interval corresponding to cut_point."""

    results = []
    for i, point in enumerate(center_linestring.coords):
        p = Point(point)
        results.append( (p.distance(cut_point), p, i))
    results.sort()
    before_cut_point = results[0][1]
    before_cut_index = results[0][2]
    after_cut_point = results[1][1]
    after_cut_index = results[1][2]

    l = LineString((before_cut_point, after_cut_point))
    before_cut_time = time.strptime("2017/08/21 %s" % times[before_cut_index], "%Y/%m/%d %H:%M")
    after_cut_time = time.strptime("2017/08/21 %s" % times[after_cut_index], "%Y/%m/%d %H:%M")
    t0 = time.mktime(before_cut_time)
    t1 = time.mktime(after_cut_time)
    dt = t1 - t0
    idt = dt * l.project(cut_point)
    interp_time = time.localtime(t0 + idt)
    return interp_time

def main():
    args = get_arguments()

    # Extract times and points from official NASA data
    times, points = parse_html(open(args.eclipse_path_html))
    # Extract the northern limit, the central line, and southern limit
    # of the path (defining which regions experience totality).
    northern_limit = [point[0] for point in points]
    central_line = [point[1] for point in points]
    southern_limit = [point[2] for point in points]
    northern_limit_linestring = LineString(northern_limit)
    southern_limit_linestring = LineString(southern_limit)
    center_linestring = LineString(central_line)

    # Map of central line points to times
    # Stored so we can convert
    central_point_to_time = dict(zip(central_line, times))

    us_map = load_map(args.us_map_file)
    main_us = us_map.boundary[78:79]
    points = us_shape_to_points(main_us)
    us_map_polygon = Polygon(points)

    northern_limit_clipped_by_us = northern_limit_linestring.intersection(us_map_polygon)
    southern_limit_clipped_by_us = southern_limit_linestring.intersection(us_map_polygon)
    center_clipped_by_us = center_linestring.intersection(us_map_polygon)

    # The eclipse path lines clipped by the US map got cut.  To serialize the
    # output, we need to interpolate the times from the eclipse path
    # corresponding to the cut points.
    first_point = Point(center_clipped_by_us.coords[0])
    first_interp_time = interpolate_time(first_point, center_linestring, times)
    first_interp_time_string = time.strftime("%H:%M", first_interp_time)

    last_point = Point(center_clipped_by_us.coords[-1])
    last_interp_time = interpolate_time(last_point, center_linestring, times)
    last_interp_time_string = time.strftime("%H:%M", last_interp_time)

    # Insert the interpolated times into the dictionary of points to times
    central_point_to_time[(first_point.coords[0][0], first_point.coords[0][1])] = first_interp_time_string
    central_point_to_time[(last_point.coords[0][0], last_point.coords[0][1])] = last_interp_time_string

    obs = ephem.Observer()
    sun = ephem.Sun()
    moon = ephem.Moon()

    # Write an eclipse path file with the same format as the input, but clipped
    # to US map boundary, with interpolated times at the beginning and end.
    f = open(args.eclipse_path_output, "w")
    for i, center in enumerate(center_clipped_by_us.coords):
        dt = central_point_to_time[center]
        obs.lat = math.radians(center[0])
        obs.lon = math.radians(center[1])
        dt0 = "2017/08/21 %s" % dt
        d = ephem.Date(str(dt0))
        obs.date = d
        sun.compute(obs)
        moon.compute(obs)
        alt = math.floor(math.degrees(sun.alt))
        az = math.floor(math.degrees(sun.az))
        size_ratio = moon.size / sun.size

        n=fmt_loc_pair(northern_limit_clipped_by_us.coords[i])
        c=fmt_loc_pair(center)
        s=fmt_loc_pair(southern_limit_clipped_by_us.coords[i])

        # TODO(dek): The path width and peak length are fake data that should be
        # copied/interpolated from the input
        f.write("%6s  %sN %sW %sN %sW %sN %sW  %5.3f %3d %3d   99  01m57.3s\n" %
                (dt, n[0], n[1], s[0], s[1], c[0], c[1], size_ratio, alt, az))

    # Boundary polygon
    c = []
    c.append(center_clipped_by_us.coords[0])
    c.extend(northern_limit_clipped_by_us.coords)
    c.append(center_clipped_by_us.coords[-1])
    # Reverse direction so we can add it to polygon in the correct order
    c.extend(southern_limit_clipped_by_us.coords[::-1])
    boundary = Polygon(c)

if __name__ == '__main__':
    main()
