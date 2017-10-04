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

import string
import random

def minute_seconds_to_decimal(ms):
  """Convert value in minute.seconds to decimal"""
  return ms / 60.

def string_to_decimal(s):
  """Convert string like 45 19.3N to (45, 19.3)"""
  return int(s[0:3]) + minute_seconds_to_decimal(float(s[4:-1]))

def load_data(lines):
  """Load data file resembling NASA eclipse path data."""
  times = []
  points = []
  in_limits = False
  for line in lines:
    if line.startswith(' Limits'):
      in_limits  = not in_limits
      continue
    if in_limits:
      if line.startswith('#'):
        continue
      line = line.strip()
      if line == '':
        continue
      t = line[0:5]
      nlat = line[7:16]
      nlon = line[17:26]
      slat = line[27:36]
      slon = line[37:46]
      clat = line[47:56]
      clon = line[57:66]
      msdiam = line[68:73]
      sunalt = line[75:77]
      sunazm = line[79:81]
      pathwidth = line[84:86]
      dur = line[88:]

      if nlat == '    -    ':
        continue
      nlat = string_to_decimal(nlat)
      nlon = string_to_decimal(nlon)
      clat = string_to_decimal(clat)
      clon = string_to_decimal(clon)
      slat = string_to_decimal(slat)
      slon = string_to_decimal(slon)

      times.append(t)
      points.append( ((nlat, -nlon), (clat, -clon), (slat, -slon)))
  return times, points

def load_stripped_data(lines):
  """Load stripped data file resembling NASA eclipse path data.  This
     routine exists to parse files like
     eclipse_gis/data/eclipse_data.txt which have been partially
     stripped of irrelevant data.
  """
  times = []
  points = []
  in_limits = False
  for line in lines:
    if line.startswith('#'):
      continue
    line = line.strip()
    if line == '':
      continue
    t = line[0:5]
    nlat = line[7:16]
    nlon = line[17:26]
    slat = line[27:36]
    slon = line[37:46]
    clat = line[47:56]
    clon = line[57:66]
    msdiam = line[68:73]
    sunalt = line[75:77]
    sunazm = line[79:81]
    pathwidth = line[84:86]
    dur = line[88:]

    if nlat == '    -    ':
      continue
    nlat = string_to_decimal(nlat)
    nlon = string_to_decimal(nlon)
    clat = string_to_decimal(clat)
    clon = string_to_decimal(clon)
    slat = string_to_decimal(slat)
    slon = string_to_decimal(slon)

    times.append(t)
    points.append( ((nlat, -nlon), (clat, -clon), (slat, -slon)))
  return times, points

def load_tsv(filename):
  f = open(filename)
  lines = f.readlines()
  points = []
  for line in lines:
    point = map(float, line.split("\t"))
    points.append(point)
  from shapely.geometry import Polygon, Point
  eclipse_boundary = Polygon(points)
  return eclipse_boundary

def generate_polygon(points):
  from shapely.geometry import Polygon, Point, LineString
  p = []
  p.append(points[0][1])
  for point in points:
    p.append(point[0])
  p.append(points[-1][1])
  for point in points[::-1]:
    p.append(point[2])
  eclipse_boundary = Polygon(p)

  p = []
  for point in points:
    p.append(point[1])
  center_line = LineString(p)

  return eclipse_boundary, center_line

class EclipseGIS:
  def __init__(self, boundary, center_line):
    self.eclipse_boundary = boundary
    self.center_line = center_line

  def test_point_within_eclipse_boundary(self, point):
    return self.eclipse_boundary.contains(point)

  def find_nearest_point_on_line(self, point):
    return self.center_line.interpolate(self.center_line.project(point))

  def interpolate_nearest_point_on_line(self, point):
    p = self.find_nearest_point_on_line(point)
    return self.center_line.project(p, normalized=True)

  def get_random_point_in_polygon(self):
    from shapely.geometry import Point
    poly = self.eclipse_boundary
    min_x, min_y, max_x, max_y = poly.bounds
    while True:
      p = Point(random.uniform(min_x, max_x), random.uniform(min_y, max_y))
      if poly.contains(p):
        return p
