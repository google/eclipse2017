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

import math
import ephem
import traceback
import pickle
import os
import numpy as np
import string
import argparse
import cv2
from multiprocessing import Pool
from rawkit.raw import Raw

blacklist = ['9bb78815fbfb44fbec67d2cabc3378562422f59ee91fa5e864775fa3e25665df', '7a972430e284eef81294b95b32f4c14be31a896b53149b40863ef659be1a2131']

def getRescaledDimensions(width, height, max_w, max_h):
    given_ratio = max_w / float(max_h)
    ratio = width / float(height)
    if ratio > given_ratio:
        target_width = max_w
    else:
        target_width = int(round(ratio * float(max_w)))
    if ratio <= given_ratio:
        target_height = max_h
    else:
        target_height = int(round(ratio * float(max_h)))
    return target_width, target_height

def pad_height(image):
    height, width, _ = image.shape
    border_x = 0
    border_y = int(round(1080-height)/2.)
    image = cv2.copyMakeBorder(image, border_y, border_y,
                               border_x, border_x,
                               cv2.BORDER_CONSTANT, value=[0,0,0,0])
    return image

def pad_width(image):
    height, width, _ = image.shape
    border_x = int(round(1920-width)/2.)
    border_y = 0
    image = cv2.copyMakeBorder(image, border_y, border_y,
                               border_x, border_x,
                               cv2.BORDER_CONSTANT, value=[0,0,0,0])
    return image

def crop_height(image):
    height, width, _ = image.shape
    border_x = 0
    border_y = int(round(height-1080)/2.)
    image = image[border_y:height-border_y, border_x:width-border_x]
    return image

def crop_width(image):
    height, width, _ = image.shape
    border_x = int(round(width-1920)/2.)
    border_y = 0
    image = image[border_y:height-border_y, border_x:width-border_x]
    return image

def rescale_photo(fname, image, cx, cy, r):
    image_cols, image_rows, _ = image.shape
    if cx - r >= 0 and cx + r < image_rows and cy - r >= 0 and cy + r < image_cols:
        center_y = image_cols / 2
        center_x = image_rows / 2
        dx = (center_x-cx)
        dy = (center_y-cy)
        M = np.float32([[1,0,dx],[0,1,dy]])
        # Translate center of sun to center of image
        image = cv2.warpAffine(image,M,(image_rows,image_cols))
        image_rows, image_cols, _ = image.shape
        ratio = 100. / r
        target_width = int(round(image_cols * ratio))
        target_height = int(round(image_rows * ratio))
        # Scale image so sun is 100 pixels
        image = cv2.resize(image, (target_width, target_height))

        new_rows, new_cols, _ = image.shape

        if new_cols > 1920 and new_rows > 1080:
            # image is too wide and too tall
            image = crop_width(image)
            image = crop_height(image)
        elif new_cols > 1920 and new_rows <= 1080:
            # image is too wide and too short
            image = crop_width(image)
            image = pad_height(image)
        elif new_cols <= 1920 and new_rows > 1080:
            # image is too skinny and too tall
            image = crop_height(image)
            image = pad_width(image)
            # crop height
            # pad width
        elif new_cols <= 1920 and new_rows <= 1080:
            # image is too skinny and too short
            image = pad_height(image)
            image = pad_width(image)
        elif new_cols == 1920 and new_rows == 1080:
            pass
        else:
            print new_cols, new_rows
            raise UriahLogicError

        image = cv2.resize(image, (1920, 1080))
        return image
    else:
        print "Unsuccessfully processed: eclipse clipped by edge"
        print "cx:", cx
        print "cy:", cy
        print "r:", r
        print "image_rows:", image_rows
        print "image_cols:", image_cols
        return None

def rotate_photo(image, fname, cx, cy, lat, lon, dt):
    obs = ephem.Observer()
    obs.lat = math.radians(lat)
    obs.lon = math.radians(lon)

    sun = ephem.Sun()

    d = ephem.Date(dt)
    obs.date = d
    sun.compute(obs)
    angle = sun.parallactic_angle() # in rad
    rot_mat = cv2.getRotationMatrix2D((image.shape[1]/2, image.shape[0]/2), math.degrees(angle), 1.0)
    image = cv2.warpAffine(image, rot_mat, (image.shape[1], image.shape[0]), flags=cv2.INTER_CUBIC)
    return image

def process_image(work):
    try:
        fname = work['fname']
        if os.path.basename(fname) in blacklist:
            print "Image", fname, "is in blacklist"
            return fname, False
        rescaled_directory = work['rescaled_directory'] 
        new_fname = os.path.join(rescaled_directory, os.path.basename(fname) + ".rescaled.png")
        if os.path.exists(new_fname):
            print "Image", fname, "already has rescaled output:", new_fname
            return fname, True

        cx = work['cx']
        cy = work['cy']
        r = work['r']
        image = cv2.imread(fname)
        if image is None:
            with Raw(filename=fname) as raw:
                tiff_output_file = fname + ".tiff"
                raw.save(filename=tiff_output_file)
                image = cv2.imread(tiff_output_file)
                if image is None:
                    print "failed to read image after tiff conversion"
                    return fname, False
        elif image.shape == (120, 160, 3) or image.shape == (171, 256, 3):
            with Raw(filename=fname) as raw:
                tiff_output_file = fname + ".tiff"
                raw.save(filename=tiff_output_file)
                image = cv2.imread(tiff_output_file)
                if image is None:
                    print "failed to read image after tiff conversion"
                    return fname, False
        image = rescale_photo(fname, image, cx, cy, r)
        if image is None:
            print "Unable to rescale photo:", fname
            return fname, False
        metadata = work['metadata']
        # Apply field rotation
        if metadata.has_key('equatorial_mount') and metadata['equatorial_mount'] == False:
            try:
                lat = metadata['lat']
                lon = metadata['lon']
                dt = metadata['image_datetime']
            except KeyError:
                print "Failed to look up lat, lon, or datetime"
                return fname, False
            # image = rotate_photo(image, fname, cx, cy, lat, lon, dt)
            # cv2.circle(image, (20, 20),  10, (0, 255, 0), thickness=-1)
        elif metadata.has_key('equatorial_mount') and metadata['equatorial_mount'] == True:
            pass
            # cv2.circle(image, (20, 20),  10, (0, 0, 255), thickness=-1)
        else:
            pass
            # cv2.circle(image, (20, 20),  10, (0, 255, 0), thickness=-1)
        
        
        if image is not None:
            params = [cv2.IMWRITE_PNG_COMPRESSION, 9]
            cv2.imwrite(new_fname, image, params)
            return fname, True
        else:
            return fname, False
    except Exception as e:
        print "Failed to process work %s, exception: %s" % (work, str(e))
        traceback.print_exc(limit=50)
        return fname, False
