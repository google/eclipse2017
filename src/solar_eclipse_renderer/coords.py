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

def horizontal_to_cartesian(altitude, azimuth):
    """Convert a "horizontal" coordinate given in altitude and azimuth to the
    corresponding 3D cartesian location."""
    theta = math.pi / 2 - math.radians(altitude)
    phi = math.radians(-azimuth)
    x = math.sin(phi) * math.sin(-theta)
    y = math.sin(theta) * math.cos(phi)
    z = math.cos(theta)
    return x, y, z

def scale_vector(vector, scale):
    """Scale a 3D vector's components by scale."""
    return vector[0] * scale, vector[1] * scale, vector[2] * scale
