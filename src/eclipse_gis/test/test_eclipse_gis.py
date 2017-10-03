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

"""Tests for eclipse_gis."""
import sys
sys.path.append("../src")
from eclipse_gis import eclipse_gis
import unittest2
from shapely.geometry import Point, Polygon, LineString

test_boundary = Polygon( ((-1,-1), (-1, 1), (1, 1), (1, -1)) )
test_center = LineString( ((-1, 0), (1, 0)) )

class EclipseGisTest(unittest2.TestCase):
  def setUp(self):
    self.eg = eclipse_gis.EclipseGIS(test_boundary, test_center)

  def tearDown(self):
    self.eg = None

  def testPointIsInPolygon(self):
    point = Point((0, 0))
    self.assertTrue(self.eg.test_point_within_eclipse_boundary(point))

  def testPointIsNotInPolygon(self):
    point = Point((42, 42))
    self.assertFalse(self.eg.test_point_within_eclipse_boundary(point))

  def testNearestPointInPolygon(self):
    point = Point((-0.5, 0.75))
    np = self.eg.find_nearest_point_on_line(point)
    self.assertEqual(np, Point(-0.5, 0))

  def testRandomPointIsInPolygon(self):
    rp = self.eg.get_random_point_in_polygon()
    self.assertTrue(self.eg.test_point_within_eclipse_boundary(rp))

if __name__ == '__main__':
  unittest2.main()
