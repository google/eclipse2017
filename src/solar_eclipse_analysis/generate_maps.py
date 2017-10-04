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

import traceback
import tempfile
import StringIO
import pickle
import os
import numpy as np
import string
import argparse
import cv2
from map_util import load_path, points_to_latlong
from multiprocessing import Pool
from PIL import Image
import matplotlib.cm as cm
import matplotlib # Force matplotlib to not use any Xwindows backend
matplotlib.use('Agg')
from matplotlib import pyplot as plt
from mpl_toolkits.basemap import Basemap
from matplotlib.patches import Polygon, Circle
from functools import partial
from map_util import points_to_latlong
from shapely.geometry import Polygon, Point, LineString

def get_arguments():
    parser = argparse.ArgumentParser(description='Map image data.')
    parser.add_argument('--input', type=str, default="extracted_metadata.pkl")
    parser.add_argument('--eclipse_path_data', type=str, default="eclipse_path_data.txt")
    parser.add_argument('--umbra_polys', type=str, default='umbra_polys.pkl')
    parser.add_argument('--directory', type=str, default="map")
    parser.add_argument('--data_directory', type=str, default="data")
    parser.add_argument('--movie_stats', type=str, default="movie_stats.txt")

    return parser.parse_args()

def draw_eclipse_umbra(ax, map, poly):
    lons, lats, colors = points_to_latlong(poly.boundary.coords)
    map.plot(lons, lats, marker='.', color="black", markersize=0.5, linewidth=0.2, zorder=2, latlon=True)

def draw_photo_pin(data_directory, ax, map, photo_lon, photo_lat):
    x_size, y_size = 1.3, 1.3*1.78
    x0, y0 = map(photo_lon - x_size/2., photo_lat - y_size/2.)
    x1, y1 = map(photo_lon + x_size/2., photo_lat + y_size/2.)

    im = plt.imread(os.path.join(data_directory, 'Map_pin.png'))
    plt.imshow(im, zorder=3, extent=(x0, x1, y0, y1))

def get_photo_selection(photo_selections, i):
    counter = i
    while counter >= 0:
        if photo_selections.has_key(counter) and photo_selections[counter] is not None:
            return photo_selections[counter]
        counter -= 1
    return None

def render_map(directory, data_directory, input_):
    try:
        i = input_['i']
        length = input_['length']
        eclipse_path_data = input_['eclipse_path_data']
        movie_frame = input_['movie_frame']
        poly = input_['poly']
        poly_dt = input_['poly_dt']
        path = input_['path']
        path_data = input_['path_data']


        # point = path.center_line.interpolate(bin_value, normalized=True)
        # bin_lat, bin_lon = point.x, point.y

        dpi = 300
        width = 321
        height = 204
        scaled_width = width / float(dpi)
        scaled_height = height / float(dpi)
        fig = plt.figure(dpi=dpi, figsize=(scaled_width, scaled_height))
        map = Basemap(
            llcrnrlon=-119.5, llcrnrlat=24.5,
            urcrnrlon=-66, urcrnrlat=47,
            projection='lcc',
            lat_1=33, lat_2=45,
            lat_0=39.828, lon_0=-98.579)
        base_color = 'white'
        border_color = 'black'
        boundary_color = 'none'
        map.drawmapboundary(color=boundary_color)
        # map.plot(path_data[1], path_data[0], color='green', marker='.', markersize=0.0001, latlon=True, zorder=1)
        ax = fig.gca()
        if movie_frame is not None:
            photo_lat = movie_frame[1]
            photo_lon = movie_frame[2]
            draw_photo_pin(data_directory, ax, map, photo_lon, photo_lat)
        draw_eclipse_umbra(ax, map, poly)

        fig.subplots_adjust(bottom=0, left=0, right=1, top=1, wspace=0, hspace=0)
        plt.tight_layout(pad=0.0, w_pad=0.0, h_pad=0)
        # plt.show()
        fname = os.path.join(directory, "marker.%05d.png" % i)
        fig.savefig(fname, dpi=dpi, transparent=True)
        plt.close(fig)

        map_fname = os.path.join(data_directory, "Grey_map_withline.png")
        im1 = Image.open(map_fname)
        im2 = Image.open(fname)

        a = 1
        b = 0
        c = +7 #left/right (i.e. 5/-5)
        d = 0
        e = 1
        f = -7 #up/down (i.e. 5/-5)
        im2_tx = im2.transform(im2.size, Image.AFFINE, (a, b, c, d, e, f))

        comp = Image.alpha_composite(im1, im2_tx)
        fname = os.path.join(directory, "map.%05d.png" % i)
        comp.save(fname)

    except Exception as e:
        print "exception in render_map on", i
        traceback.print_exc(limit=50)

def main():
    args  = get_arguments()
    f = open(args.movie_stats)
    lines = f.readlines()
    lines = [line.strip().split() for line in lines]
    movie_frames = dict([ (int(line[0]), (line[1], float(line[2]), float(line[3]))) for line in lines])

    polys = pickle.load(open(args.umbra_polys))
    r = pickle.load(open(args.input))
    for i, fname in enumerate(r):
        d = r[fname]
        lat = d['lat']
        lon = -d['lon']
        dt = d['image_datetime']
        point = Point(lon, lat)

    inputs = []
    path = load_path(args.eclipse_path_data)
    path_data = points_to_latlong(path.eclipse_boundary.exterior.coords)
    for i, p in enumerate(polys):
        poly, poly_centroid, poly_dt = p
        if i in movie_frames:
            input_ = {
                'i': i,
                'length': len(polys),
                'poly': poly,
                'poly_dt': poly_dt,
                'movie_frame': movie_frames[i],
                'eclipse_path_data': args.eclipse_path_data,
                'path': path,
                'path_data': path_data
            }
            inputs.append(input_)
    # Pre-render map images
    if args.directory is None:
        print "Must set directory for map output via --directory"
    else:
        # render_map(args.directory, args.data_directory, inputs[13])
        p = Pool(64)
        r = partial(render_map, args.directory, args.data_directory)
        p.map(r, inputs)

if __name__ == '__main__':
    main()
