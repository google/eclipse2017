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

"""Map locations to be rendered.

Maps the locations created by create_locations.  Useful for debugging
the image rendering code inputs.
"""

import argparse
from shapely.geometry import shape
from eclipse_gis import eclipse_gis
import matplotlib.cm as cm
import matplotlib # Force matplotlib to not use any Xwindows backend
matplotlib.use('Agg')
from matplotlib import pyplot as plt
from mpl_toolkits.basemap import Basemap
import pickle
from util import load_path

def get_arguments():
    parser = argparse.ArgumentParser(description='Map image data.')
    parser.add_argument('--output', type=str, default='/tmp/test.png')
    parser.add_argument('--eclipse_path_data', type=str, default="eclipse_path_data.txt")
    parser.add_argument('--inside_filename', type=str, default="locations_inside.pkl")
    parser.add_argument('--outside_filename', type=str, default="locations_outside.pkl")
    return parser.parse_args()

def main():
    args  = get_arguments()

    path = load_path(args.eclipse_path_data)

    # The funny constants define the lower left and upper right
    # corners (lat and lon) of the map boundary
    map = Basemap(llcrnrlat=22, llcrnrlon=-119, urcrnrlat=49, urcrnrlon=-64,
                  projection='lcc',lat_1=33,lat_2=45,lon_0=-95,
                  resolution='l')
    base_color = 'white'
    border_color = 'lightgray'
    boundary_color = 'gray'
    map.fillcontinents(color=base_color, lake_color=border_color)
    map.drawstates(color=border_color)
    map.drawcoastlines(color=border_color)
    map.drawcountries(color=border_color)
    map.drawmapboundary(color=boundary_color)

    points = pickle.load(open(args.inside_filename))
    lats = []
    lons = []
    colors = []
    for point in points:
        lat = point[0]
        lon = point[1]
        colors.append('r')
        lats.append(lat)
        lons.append(lon)

    points = pickle.load(open(args.outside_filename))
    for point in points:
        lat = point[0]
        lon = point[1]
        colors.append('g')
        lats.append(lat)
        lons.append(lon)

    # Draw locations as colored points (red for "inside" and green for
    # "outside)
    map.scatter(lons, lats, marker='.', c=colors, edgecolors='none', s=3, latlon=True, zorder=2, cmap=cm.plasma)
    fig = matplotlib.pyplot.gcf()
    fig.set_size_inches(18.5, 10.5)

    xs = []
    ys = []
    # Draw the eclipse path boundary as path
    for point in path.eclipse_boundary.exterior.coords:
        ys.append(point[0])
        xs.append(point[1])
    map.plot(xs, ys, latlon=True, alpha=0.5, zorder=3)

    plt.savefig(args.output, dpi=100)

if __name__ == '__main__':

    main()
