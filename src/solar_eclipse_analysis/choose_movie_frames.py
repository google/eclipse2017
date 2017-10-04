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

import pprint
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
from collections import Counter
RES_X=1920
RES_Y=1080


c = Counter()

def get_arguments():
    parser = argparse.ArgumentParser(description='Render movie.')
    parser.add_argument('--directory', type=str, default="")
    parser.add_argument('--metadata', type=str, default="extracted_metadata.pkl")
    parser.add_argument('--umbra_polys', type=str, default='umbra_polys.pkl')
    parser.add_argument('--photo_selections', type=str, default='photo_selections.pkl')
    parser.add_argument('--rescaled_directory', type=str, default="rescaled")
    parser.add_argument('--movie_blacklist', type=str, default="data/movie_blacklist.txt")
    parser.add_argument('--movie_stats', type=str, default="movie_stats.txt")
    parser.add_argument('--movie_frame_choices', type=str, default="movie_frame_choices.pkl")
    return parser.parse_args()

def get_rescaled(fname, metadata, directory, rescaled_directory):
    # TODO(dek): move rescaling to its own function
    rescaled_fname = fname + ".rescaled.png"
    rescaled = os.path.join(rescaled_directory, rescaled_fname)
    if not os.path.exists(rescaled):
        print "Unable to find cached rescaled image for", fname
        return None
    image = cv2.imread(rescaled, cv2.IMREAD_UNCHANGED)
    if image is None:
        print "Failed to read image from", rescaled
        return None
    b_channel, g_channel, r_channel = cv2.split(image)
    alpha_channel = np.ones(b_channel.shape, dtype=b_channel.dtype) * 255
    image = cv2.merge((b_channel, g_channel, r_channel, alpha_channel))

    return image

def get_photo_selection(photo_selections, i):
    counter = i
    while counter >= 0:
        if photo_selections.has_key(counter) and photo_selections[counter] is not None:
            return photo_selections[counter]
        counter -= 1
    return None


def filter_rescaled_photo_selections(i, photo_selections, rescaled_photos):
    print "Frame", i
    photo_selection = get_photo_selection(photo_selections, i)
    results = []
    if photo_selection is not None:
        for j in range(len(photo_selection)):
            fname = photo_selection[j][1]
            if fname in rescaled_photos:
                results.append(photo_selection[j])

    return i, results

def choose_movie_frame(i, rescaled_photo_selection, metadata):
    if len(rescaled_photo_selection) == 0:
        return i, None
    for rescaled_photo in rescaled_photo_selection:
        fname = rescaled_photo[1]
        # if metadata.has_key(fname):
        #     eq = metadata[fname].get('equatorial_mount', False)
        #     if eq == False:
        #         print "Skipping", fname, "due to non-equatorial mount"
        #         continue
        c.update([fname])
        if c[fname] > 8:
            print "Skipping", fname, "due to threshold"
            continue
        else:
            print "Selecting", fname
            return i, rescaled_photo
    else:
        print "Exhausted, selecting last"
        return i, rescaled_photo_selection[-1]


    
def main():
    args  = get_arguments()
    photo_selections = pickle.load(open(args.photo_selections))
    movie_blacklist = [line.strip() for line in open(args.movie_blacklist).readlines()]

    s = set()
    frame = photo_selections.values()
    for photos in frame:
        for photo in photos:
            fname = photo[1]
            if fname not in movie_blacklist:
                s.add(photo[1])

    print "Total of", len(s), "photos"
    fnames = list(s)
    fnames.sort()

    rescaled_photos = set()
    for fname in fnames:
        f = os.path.join(args.rescaled_directory, fname + ".rescaled.png")
        if os.path.exists(f):
            rescaled_photos.add(fname)

    print "Total of", len(rescaled_photos), "rescaled photos"
    
    polys = pickle.load(open(args.umbra_polys))
    blahs = []
    metadata = pickle.load(open(args.metadata))
    rescaled_photo_selections = []
    for i, poly in enumerate(polys):
        rescaled_photo_selections.append(filter_rescaled_photo_selections(i, photo_selections, rescaled_photos))

    rescaled_photo_selections = dict(rescaled_photo_selections)

    movie_frames = []
    for i, poly in enumerate(polys):
        movie_frames.append(choose_movie_frame(i, rescaled_photo_selections[i], metadata))
    movie_frames = dict(movie_frames)

    pickle.dump(movie_frames, open(args.movie_frame_choices, "wb"))
 
    f = open(args.movie_stats, "wb")
    keys = movie_frames.keys()
    keys.sort()
    for key in keys:
        movie_frame = movie_frames[key]
        if movie_frame is None: continue
        dist, fname, photo_lat, photo_lon, image_datetime, width, height = movie_frame
        f.write("%d %s %f %f\n" % (key, fname, photo_lat, photo_lon))
    f.close()

if __name__ == '__main__':
    main()
