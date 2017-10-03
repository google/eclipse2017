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

from shapely.geometry import LineString
from eclipse_gis import eclipse_gis
from BeautifulSoup import BeautifulSoup
import shapefile
from shapely.geometry import shape

def parse_html(eclipse_path_html):
    doc = BeautifulSoup(eclipse_path_html, convertEntities=BeautifulSoup.HTML_ENTITIES)
    data =  doc.body.find('pre').text.replace("\r", "\n").split("\n")
    times, points = eclipse_gis.load_data(data)
    return times, points

def load_map(map_path):
    sh = shapefile.Reader(map_path)
    feature = sh.shapeRecords()[0]
    first = feature.shape.__geo_interface__
    shp_geom = shape(first)
    return shp_geom

def points_to_latlong(points, color='r'):
    lats = []
    lons = []
    colors = []
    for point in points:
        lat = point[0]
        lon = point[1]
        colors.append(color)
        lats.append(lat)
        lons.append(lon)
    return lats, lons, colors

def us_shape_to_points(main_us):
    points = []
    for line in main_us.geoms:
        for point in line.coords:
            points.append((point[1], point[0]))
    return points

def load_path(eclipse_path_data):
    times, points = eclipse_gis.load_stripped_data(open(eclipse_path_data).readlines())
    boundary, center = eclipse_gis.generate_polygon(points)
    eg = eclipse_gis.EclipseGIS(boundary, center)
    return eg
