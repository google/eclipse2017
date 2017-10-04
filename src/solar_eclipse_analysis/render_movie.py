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

import shutil
import glob
import functools
import traceback
import tempfile
import StringIO
import pickle
import os
import numpy as np
import string
import argparse
import cv2
from find_circles import findCircles
from rescale_photos import process_image
from map_util import load_path, points_to_latlong
from multiprocessing import Pool
from PIL import Image, ImageDraw, ImageFont
import matplotlib.cm as cm
import matplotlib # Force matplotlib to not use any Xwindows backend
matplotlib.use('Agg')
from matplotlib import pyplot as plt
from mpl_toolkits.basemap import Basemap
from functools import partial
from rawkit.raw import Raw

RES_X=1920
RES_Y=1080

def get_arguments():
    parser = argparse.ArgumentParser(description='Render movie.')
    parser.add_argument('--directory', type=str, default="")
    parser.add_argument('--metadata', type=str, default="extracted_metadata.pkl")
    parser.add_argument('--umbra_polys', type=str, default='umbra_polys.pkl')
    parser.add_argument('--map_directory', type=str, default='map')
    parser.add_argument('--data_directory', type=str, default='data')
    parser.add_argument('--output_directory', type=str, default='movie')
    parser.add_argument('--photo_selections', type=str, default='photo_selections.pkl')
    parser.add_argument('--rescaled_directory', type=str, default="rescaled")
    parser.add_argument('--movie_blacklist', type=str, default="data/movie_blacklist.txt")
    parser.add_argument('--movie_stats', type=str, default="movie_stats.txt")
    return parser.parse_args()

def hisEqulColor(img):
    ycrcb=cv2.cvtColor(img,cv2.COLOR_BGR2YCR_CB)
    channels=cv2.split(ycrcb)
    # create a CLAHE object
    clahe = cv2.createCLAHE()
    channels[0] = clahe.apply(channels[0])
    cv2.merge(channels,ycrcb)
    cv2.cvtColor(ycrcb,cv2.COLOR_YCR_CB2BGR,img)

def get_rescaled(fname, rescaled_directory):
    rescaled_fname = fname + ".rescaled.png"
    rescaled = os.path.join(rescaled_directory, rescaled_fname)
    image = cv2.imread(rescaled, cv2.IMREAD_UNCHANGED)
    if image is None:
        print "Failed to read image from", rescaled
        return i, None
    # hisEqulColor(image)

                
    b_channel, g_channel, r_channel = cv2.split(image)
    alpha_channel = np.ones(b_channel.shape, dtype=b_channel.dtype) * 255
    image = cv2.merge((b_channel, g_channel, r_channel, alpha_channel))
    return image


def stamp_and_number_image(directory, rescaled_directory, map_directory, data_directory, output_directory, blah):
    try:
        t = (RES_Y, RES_X, 4)
        
        i = blah['i']
        fname = blah['fname']
        poly = blah['poly']

        image = get_rescaled(fname, rescaled_directory)

        map_fname = os.path.join(map_directory, "map.%05d.png" % i)
        map_pad = np.zeros(t, dtype=np.uint8)
        map_ = cv2.imread(map_fname, cv2.IMREAD_UNCHANGED)
        s = map_.shape
        map_pad[t[0]-s[0]-40:t[0]-40, t[1]-s[1]-40:t[1]-40] = map_

        
        image = cv2.addWeighted(map_pad, 1, image, 1, 0)

        berkeley_logo_pad = np.zeros(t, dtype=np.uint8)
        berkeley_logo = cv2.imread(os.path.join(data_directory, "logo_footer_berkeley.png"), cv2.IMREAD_UNCHANGED)
        s = berkeley_logo.shape
        berkeley_logo_pad[40:40+s[0], 1700:1700+s[1]] = berkeley_logo
        image = cv2.addWeighted(berkeley_logo_pad, 1, image, 1, 0)

        google_logo_pad = np.zeros(t, dtype=np.uint8)
        google_logo = cv2.imread(os.path.join(data_directory, "logo_footer_google.png"), cv2.IMREAD_UNCHANGED)
        s = google_logo.shape
        google_logo_pad[40:40+s[0], 1800:1800+s[1]] = google_logo
        image = cv2.addWeighted(google_logo_pad, 1, image, 1, 0)

        megamovie_logo_pad = np.zeros(t, dtype=np.uint8)
        megamovie_logo = cv2.imread(os.path.join(data_directory, "EclipseMovie_logo_crop.png"), cv2.IMREAD_UNCHANGED)
        s = megamovie_logo.shape
        megamovie_logo_pad[40:40+s[0], 40:40+s[1]] = megamovie_logo
        image = cv2.addWeighted(megamovie_logo_pad, 1, image, 1, 0)

        im = Image.new("RGBA", (image.shape[1], image.shape[0]), (0,0,0,0))
        draw = ImageDraw.Draw(im)
        font = ImageFont.truetype("ProductSans-Regular.ttf", 39)

        txt = "Eclipse Megamovie 2017"
        draw.text((140, 45), txt, (255,255,255,255), font=font)
        tfmt = poly[2].strftime("%H:%M:%S")
        txt = "Time at Umbral Center: %s" % tfmt
        draw.text((1350, 1040), txt, (255,255,255,255), font=font)
        # txt = "Frame #%d %s" % (i, fname)
        # draw.text((20, 1040), txt, (255,255,255,255), font=font)
        x = cv2.cvtColor(np.asarray(im), cv2.COLOR_RGB2BGR)
        b_channel, g_channel, r_channel = cv2.split(x)
        alpha_channel = np.ones(b_channel.shape, dtype=b_channel.dtype) * 255
        x = cv2.merge((b_channel, g_channel, r_channel, alpha_channel))
        image = cv2.addWeighted( x, 1, image, 1, 0.0)

        new_fname = os.path.join(output_directory, "%05d.png" % i)
        cv2.imwrite(new_fname, image)
        return i, fname, True

    except Exception as e:
        traceback.print_exc(limit=50)
        return i, fname, False

def main():
    args  = get_arguments()

        
    f = open(args.movie_stats)
    lines = f.readlines()
    lines = [line.strip().split() for line in lines]
    movie_frames = dict([ (int(line[0]), line[1]) for line in lines])
    polys = pickle.load(open(args.umbra_polys))
    
    blahs = []
    metadata = pickle.load(open(args.metadata))
    for i, poly in enumerate(polys):
        if i in movie_frames:
            blah = {}
            blah['fname'] = movie_frames[i]
            blah['i'] = i
            blah['poly'] = poly
            blahs.append(blah)

    # results = []
    # for blah in blahs:
    #     results.append(stamp_and_number_image(args.directory, args.rescaled_directory, args.map_directory, args.data_directory, args.output_directory, blah))
        
    p = Pool(24)
    s = functools.partial(stamp_and_number_image, args.directory, args.rescaled_directory, args.map_directory, args.data_directory, args.output_directory)
    results = p.map(s, blahs)


if __name__ == '__main__':
    main()
