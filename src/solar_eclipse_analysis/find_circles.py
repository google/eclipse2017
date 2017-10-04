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
import pickle
import os
import numpy as np
import string
import argparse
import cv2
from multiprocessing import Pool
from rawkit.raw import Raw

ignore = [ '7569b99296da7ea2328065cbacb12c39fd65cbf4ba897ab078c573d998c4c470' ]

def findCircles(fname, image, circles_directory):
    f = os.path.join(circles_directory, os.path.basename(fname) + ".pkl")
    if os.path.exists(f):
        circles = pickle.load(open(f, "rb"))
        return circles
    image_cols, image_rows, _ = image.shape

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.bilateralFilter(gray, 9, 75, 75)
    gray = cv2.addWeighted(gray, 1.5, blurred, -0.5, 0)
    gray = cv2.bilateralFilter(gray, 9, 75, 75)

    # # detect circles in the image
    dp = 1
    c1 = 100
    c2 = 15
    print "start hough", fname
    circles = cv2.HoughCircles(gray, cv2.cv.CV_HOUGH_GRADIENT, dp, image_cols / 8, param1=c1, param2=c2)
    print "finish hough", fname
    pickle.dump(circles, open(f, "wb"))
    if circles is None or not len(circles):
        return None
    return circles
