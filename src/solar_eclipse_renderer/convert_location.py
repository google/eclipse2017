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

import ephem
import math
deg = math.degrees
from coords import horizontal_to_cartesian
from lune import get_lune

def convert_location(lat, lon, start_datetime, end_datetime, inclusion_threshold, dt = 1):
    """Convert a lat, lon and start to end datetime to a series of sun and moon positions.

    The resulting positions are filtered by inclusion_threshold, which
    is compared to the seperation angle.  The datetime clock is
    incremented by dt seconds by iteration."""

    obs = ephem.Observer()
    obs.lat = math.radians(lat)
    obs.lon = math.radians(lon)

    sun = ephem.Sun()
    moon = ephem.Moon()

    d = ephem.Date(start_datetime)
    pos = []

    while d < ephem.Date(end_datetime):
        obs.date = d
        sun.compute(obs)
        moon.compute(obs)
        l = get_lune(sun, moon)

        if l > inclusion_threshold:
          # print(str(d), "Sun: %.3f %.3f" % (deg(sun.alt), deg(sun.az)), "Moon: %.3f %.3f" % (deg(moon.alt), deg(moon.az)), "%.4f" % s, parallactic_angle, ph)
          r_sun=sun.size/2
          r_moon=moon.size/2
          parallactic_angle = sun.parallactic_angle()
          pos.append( (str(d), float(sun.alt), float(sun.az), float(moon.alt), float(moon.az), r_sun, r_moon, l, parallactic_angle, lat, lon))

        d = ephem.Date(d + (dt*ephem.second))
    return pos
