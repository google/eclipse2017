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

"""Update roles for a user."""

import argparse
import math
import random
from google.cloud import datastore
import common.service_account as sa

DEFAULT_PROJECT = 'eclipse-2017-test'
INVALID_USER = '-1'

def get_arguments():
  parser = argparse.ArgumentParser(description='Add a set of fake users.')
  parser.add_argument('--project_id', type=str, default=DEFAULT_PROJECT,
                      help = 'Project ID to add users to')
  parser.add_argument('--count', nargs=1, type=int, default = 0,
                      help = 'Number of fake users to add')
  return parser.parse_args()

def get_polygon():
  eclipse_points =  [[45.27, -123.44], [45.2, -121.84], [45.11, -120.31], [45.01, -118.82], [44.89, -117.39], [44.76, -116.0], [44.61, -114.65], [44.45, -113.34], [44.29, -112.08], [44.11, -110.84], [43.92, -109.64], [43.73, -108.47], [43.52, -107.33], [43.31, -106.22], [43.09, -105.13], [42.85, -104.07], [42.62, -103.03], [42.38, -102.02], [42.12, -101.02], [41.87, -100.04], [41.6, -99.09], [41.33, -98.15], [41.06, -97.23], [40.78, -96.32], [40.49, -95.43], [40.2, -94.56], [39.9, -93.69], [39.6, -92.84], [39.29, -92.01], [38.98, -91.18], [38.66, -90.37], [38.34, -89.56], [38.02, -88.77], [37.69, -87.98], [37.35, -87.2], [37.01, -86.43], [36.67, -85.67], [36.32, -84.91], [35.97, -84.16], [35.61, -83.41], [35.25, -82.67], [34.89, -81.93], [34.52, -81.19], [34.15, -80.46], [32.91, -80.43], [33.28, -81.15], [33.65, -81.88], [34.01, -82.6], [34.37, -83.33], [34.72, -84.06], [35.07, -84.79], [35.41, -85.53], [35.76, -86.27], [36.09, -87.02], [36.42, -87.78], [36.75, -88.54], [37.08, -89.31], [37.4, -90.09], [37.71, -90.88], [38.02, -91.67], [38.33, -92.48], [38.63, -93.29], [38.93, -94.12], [39.22, -94.96], [39.51, -95.82], [39.79, -96.68], [40.07, -97.56], [40.34, -98.46], [40.61, -99.37], [40.87, -100.3], [41.13, -101.25], [41.38, -102.22], [41.62, -103.2], [41.86, -104.21], [42.09, -105.24], [42.31, -106.3], [42.52, -107.38], [42.73, -108.48], [42.93, -109.62], [43.12, -110.78], [43.3, -111.97], [43.48, -113.2], [43.64, -114.47], [43.79, -115.77], [43.93, -117.12], [44.05, -118.51], [44.17, -119.94], [44.27, -121.43], [44.35, -122.98]]
  eclipse_poly =  [ {'lat': point[0], 'lng': point[1]} for point in eclipse_points ]
  return eclipse_poly

def create_user(client, user_id, eclipse_poly):
  user_key = client.key("User", user_id)
  print user_key.name
  user = datastore.Entity(key = user_key)
  user['name'] = u"Test User " + user_id
  user['email'] = u"test" + user_id + u"@example.com"
  # Get random location.
  point = eclipse_poly[random.randint(0, len(eclipse_poly) - 1)]
  u = float(random.uniform(-1.0, 1.0))
  v = float(random.uniform(-1.0, 1.0))
  user['geocoded_location'] = [point['lat'] + u, point['lng'] + v]
  print point
  print u
  print v
  print user['geocoded_location']
  client.put(user)
  user_role_key = client.key("UserRole", user_id)
  user_role = datastore.Entity(key = user_role_key)
  user_role['roles'] = [u"user"]
  # make some of them volunteers.
  if float(random.uniform(0.0, 1.0)) > 0.8:
    user_role['roles'].append(u"volunteer")

  client.put(user_role)
  return user


def main():
  args  = get_arguments()

  eclipse_poly = get_polygon()

  client = datastore.Client(args.project_id)

  for x in range(0, args.count[0]):
    user = create_user(client, str(random.randint(1, 10000000)), eclipse_poly)


if __name__ == '__main__':
  main()
