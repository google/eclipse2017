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

"""Map image data.

Draws a map of the US, with the location of each photo plotted as a point colored by its timestamp.

Useful for debugging the image ordering code."""

import logging
import argparse
from eclipse_gis import eclipse_gis
from google.cloud import datastore, storage
import image_processor.pipeline
import movie.pipeline
from common import datastore_schema as ds
import matplotlib.cm as cm
from common import constants
import matplotlib # Force matplotlib to not use any Xwindows backend
matplotlib.use('Agg')
from matplotlib import pyplot as plt
import glob
from mpl_toolkits.basemap import Basemap
from common.chunks import chunks

# This is not a valid project name (for safety)
DEFAULT_PROJECT = 'eclipse-2017-test'
def cmp_totality_ordering(item):
    return item[ds.TOTALITY_ORDERING_PROPERTY]


def get_arguments():
    parser = argparse.ArgumentParser(description='Map image data.')
    parser.add_argument('--project_id', type=str, default=DEFAULT_PROJECT)
    parser.add_argument('--output', type=str, default='/tmp/test.png')
    parser.add_argument('--eclipse_path_data', type=str, default="/app/data/eclipse_data.txt")
    return parser.parse_args()

def main():
    logging.basicConfig(level=logging.INFO,
                        format=constants.LOG_FMT_S_THREADED)
    args  = get_arguments()
    times, points = eclipse_gis.load_stripped_data(open(args.eclipse_path_data).readlines())
    datastore_client = datastore.Client(project=args.project_id)

    query = datastore_client.query(kind=ds.DATASTORE_ORIENTED_IMAGE, \
                                   order=[ds.TOTALITY_ORDERING_PROPERTY], \
                                   filters=[("image_type","=", ds.TOTALITY_IMAGE_TYPE)])
    results = query.fetch()
    results = list(results)
    results.sort(key=cmp_totality_ordering)

    d = {}
    keys = [result["original_photo"] for result in results]
    for key_chunk in chunks(keys, 1000):
        entities = datastore_client.get_multi(key_chunk)
        for entity in entities:
            d[entity.key] = entity

    map = Basemap(llcrnrlat=22, llcrnrlon=-119, urcrnrlat=49, urcrnrlon=-64,
                  projection='lcc',lat_1=33,lat_2=45,lon_0=-95)
    base_color = 'white'
    border_color = 'lightgray'
    boundary_color = 'gray'
    map.fillcontinents(color=base_color, lake_color=border_color)
    map.drawstates(color=border_color)
    map.drawcoastlines(color=border_color)
    map.drawcountries(color=border_color)
    map.drawmapboundary(color=boundary_color)

    lats = []
    lons = []
    colors = []
    for result in results:
        photo_key = result["original_photo"]
        photo = d[photo_key]
        lat = photo['lat']
        lon = -photo['lon']
        image_datetime = photo['image_datetime']
        colors.append(int(result[ds.TOTALITY_ORDERING_PROPERTY] * 100))
        lats.append(lat)
        lons.append(lon)

    # Draw photo locations as colored points
    map.scatter(lons, lats, c = colors, marker='.', edgecolors='none', s=1, latlon=True, zorder=2, cmap=cm.plasma)
    map.colorbar()

    y = [points[0][1][0]]
    x = [points[0][1][1]]
    # Draw boundary of eclipse path
    y.extend([point[0][0] for point in points])
    x.extend([point[0][1] for point in points])
    y.extend([points[-1][1][0]])
    x.extend([points[-1][1][1]])
    y.extend([point[2][0] for point in points][::-1])
    x.extend([point[2][1] for point in points][::-1])
    y.extend([points[0][1][0]])
    x.extend([points[0][1][1]])
    map.plot(x, y, latlon=True, alpha=0.5, zorder=3)

    # Draw centerline of eclipse path
    y = [point[1][0] for point in points]
    x = [point[1][1] for point in points]
    map.plot(x, y, latlon=True, alpha=0.5, zorder=3)
    plt.savefig(args.output)

if __name__ == '__main__':

    main()
