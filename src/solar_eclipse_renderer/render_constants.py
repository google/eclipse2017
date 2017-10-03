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

SUN_RADIUS = 695.700 * 1.e6
# MOON_RADIUS = 1.737 * 1.e6
# Note: artificially lowered to make in-umbra areas appear "total"
MOON_RADIUS = 1.7 * 1.e6
EARTH_MOON_DISTANCE = 355.567238 * 1.e6
SUN_EARTH_DISTANCE = 152.060 * 1e9

SEGMENTS = 100
RING_COUNT = 100

colors = (255, 0, 0), (0, 255, 0), (0, 0, 255)

RES_X = 1920
RES_Y = 1080

NORTHERN_MIN = math.radians(45)
NORTHERN_MAX = math.radians(135)
SOUTHERN_MIN = math.radians(225)
SOUTHERN_MAX = math.radians(315)
WESTERN_MIN = math.radians(-45)
WESTERN_MAX = math.radians(45)
EASTERN_MIN = math.radians(180-45)
EASTERN_MAX = math.radians(180+45)
