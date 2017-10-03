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

from eclipse_gis import eclipse_gis
times, points = eclipse_gis.load_stripped_data(open("src/eclipse_gis/data/eclipse_data.txt").readlines())
boundary, center = eclipse_gis.generate_polygon(points)
print center
eclipse_gis = eclipse_gis.EclipseGIS(boundary, center)
from shapely.geometry import Point
print eclipse_gis.find_nearest_point_on_line(Point(44.62, -117.13))
print eclipse_gis.interpolate_nearest_point_on_line(Point(44.62, -117.13))
print eclipse_gis.find_nearest_point_on_line(Point(37, -88))
print eclipse_gis.interpolate_nearest_point_on_line(Point(37, -88))
