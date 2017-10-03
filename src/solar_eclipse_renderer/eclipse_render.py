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

"""Qt application that drives the solar eclipse rendering.

This application receives the arguments defining a solar eclipse
rendering (at a location, time range, and various camera parameters).

It requires an OpenGL-capable X server, but renders offline (no
window) and exits when complete.
"""

import argparse
import piexif
import math
import ephem
import json
import sys
import os
import pickle
from eclipse_gis import eclipse_gis
import signal
from PyQt5 import QtGui, QtCore, QtWidgets
from convert_location import convert_location
from eclipse_renderer import EclipseRenderer, RES_X, RES_Y
from util import get_phase, TOTALITY, NO_ECLIPSE, PARTIAL

def write_stat(eclipse_renderer, stats, suffix, pt):
    """Write a single line of data describing the sun center and size for this time point."""
    sun_center, moon_center = eclipse_renderer.getSunMoonCenter(pt)
    c = eclipse_renderer.getSunSize(pt)
    sun_radius = c[1]
    # sun_radius_correct = eclipse_renderer.getSunSizeProj(pt)
    # print sun_radius, sun_radius_correct
    # TODO(dek): replace this hack with code a getMoonSize function that works like getSunSize
    moon_radius = sun_radius
    l = "(%d, %d, %d)" % (RES_X - sun_center[0], sun_center[1], sun_radius)
    lune = pt[7]
    if lune == 0.:
        t = 'NO_ECLIPSE'
    elif lune == 100.:
        t = 'TOTALITY'
    else:
        t = 'PARTIAL'

    if t == 'NO_ECLIPSE' or t == 'TOTAL':
        l2 = "None"
    else:
        l2 = "(%d, %d, %d)" % (RES_X - moon_center[0], moon_center[1], moon_radius)
    stats.write("%s|%s|%s|%s\n" % (suffix, t, l, l2))

def write_image(image, fname, pt, lat, lon, fov, pan):
    """Write the image corresponding to a time and space point to fname."""
    dt = pt[0]
    s = pt[7]
    image.save(fname)
    datestamp, time = dt.split(" ")
    h, m, s = time.split(":")
    timestamp = ((int(h),1), (int(m),1), (int(s),1))
    lat_pretty = ephem.degrees(math.radians(lat))
    lat_h, lat_m, lat_s = str(lat_pretty).split(":")
    lat_fmt = ((int(lat_h), 1), (int(lat_m), 1), (int(float(lat_s)), 1))
    lon_pretty = ephem.degrees(math.radians(lon))
    lon_h, lon_m, lon_s = str(lon_pretty).split(":")
    lon_fmt = ((-int(lon_h), 1), (int(lon_m), 1), (int(float(lon_s)), 1))
    exif = piexif.load(fname)
    # Update the EXIF GPS time and date
    exif['GPS'][piexif.GPSIFD.GPSLatitude ] = lat_fmt
    exif['GPS'][piexif.GPSIFD.GPSLatitudeRef ] = 'N'
    exif['GPS'][piexif.GPSIFD.GPSLongitude ] = lon_fmt
    exif['GPS'][piexif.GPSIFD.GPSLongitudeRef ] = 'W'
    exif['GPS'][piexif.GPSIFD.GPSDateStamp ] = datestamp
    exif['GPS'][piexif.GPSIFD.GPSTimeStamp ] = timestamp
    t = get_phase(s)
    # Write custom data into the MakerNote
    exif['Exif'][piexif.ExifIFD.MakerNote] = "%s|%d, %d|%d" % (t, fov, pan[0], pan[1])
    b = piexif.dump(exif)
    piexif.insert(b, fname)

class MainWindow(QtWidgets.QWidget):
    def __init__(self, fov, pan_x, pan_y, subset, index, outdir, inclusion_threshold, generate, load_file, save_file):
        super(MainWindow, self).__init__()
        self.fov = fov
        self.pan_x = pan_x
        self.pan_y = pan_y
        self.subset = subset
        self.index = index
        self.outdir = outdir
        self.inclusion_threshold = inclusion_threshold

        self.eclipse_renderer = EclipseRenderer(self.fov, (self.pan_x, self.pan_y), generate=generate, load_file=load_file, save_file=save_file)

    def run(self):
        """Driver function for iterating over and rendering time-space point images to files."""
        min_dts = "2017/08/21 16:00:00"
        max_dts = "2017/08/21 20:00:00"

        if self.subset == 'inside':
            posl = pickle.load(open("locations_inside.pkl", "rb"))
        elif self.subset == 'outside':
            posl = pickle.load(open("locations_outside.pkl", "rb"))
        else:
            raise RuntimeError, "Unrecognized subset: '%s'" % self.subset

        pos = posl[self.index]
        lat, lon = pos
        # Generate points to render, filtering by inclusion threshold
        pts = convert_location(lat, lon, min_dts, max_dts, self.inclusion_threshold, dt=30)
        # Only create dirs and write stats if there are any time points
        if len(pts):
            if not os.path.exists(self.outdir):
                os.mkdir(self.outdir)
            dir_ = os.path.join(self.outdir,
                                "%.4f,%.4f,%d,%d,%d,%s" % (
                                    lat, lon,self.fov,self.pan_x,self.pan_y,self.subset))
            if not os.path.exists(dir_):
                os.mkdir(dir_)

            stats = open(os.path.join(dir_, "stats.txt"), "w")
            for i, pt in enumerate(pts):
                suffix = "%05d.jpg" % i
                fname = os.path.join(dir_, suffix)
                write_stat(self.eclipse_renderer, stats, suffix, pt)
                image = self.eclipse_renderer.paint(pt)
                write_image(image, fname, pt, lat, lon, self.fov, (self.pan_x, self.pan_y))
            stats.close()
        sys.exit(0)

def get_arguments():
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('--fov', type=int, default=2)
    parser.add_argument('--pan_x', type=int, default=0)
    parser.add_argument('--pan_y', type=int, default=0)
    parser.add_argument('--subset', type=str, default='inside')
    parser.add_argument('--index', type=int, default=0)
    parser.add_argument('--save-file', type=str, default="random.txt")
    parser.add_argument('--load-file', type=str, default="random.txt")
    parser.add_argument('--generate', action='store_true')
    parser.add_argument('--output_dir', type=str, default="/mnt/dek/images/generated-images-7")
    parser.add_argument('--inclusion_threshold', type=float, default=95)
    return parser.parse_args()

def main():
    args  = get_arguments()
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    app = QtWidgets.QApplication(['Eclipse'])
    window = MainWindow(args.fov, args.pan_x, args.pan_y, args.subset, args.index, args.output_dir, args.inclusion_threshold, args.generate, args.load_file, args.save_file)
    QtCore.QTimer.singleShot(0, window.run)
    app.exec_()

if __name__ == '__main__':
    main()
