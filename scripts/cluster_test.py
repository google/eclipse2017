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

"""Cluster locations (debug tool)."""

import argparse
from google.cloud import datastore
import common.service_account as sa
from common.cluster_points import cluster_points, compute_centers
import matplotlib.pyplot as plt
import numpy as np

DEFAULT_PROJECT = 'eclipse-2017-test-147301'

def get_arguments():
    parser = argparse.ArgumentParser(description='Cluster locations.')
    parser.add_argument('--project_id', type=str, default=DEFAULT_PROJECT)
    return parser.parse_args()

def get_user_locations(client):
    query = client.query(kind="User")
    cursor = None
    locations = []
    while True:
        entities_count = 0
        entities = query.fetch(start_cursor=cursor, limit=1000)
        for entity in entities:
            entities_count += 1
            if entity.has_key('geocoded_location'):
                location = entity['geocoded_location']
                locations.append(location)

        if entities_count < 1000:
            break
        cursor = entities.next_page_token
    return locations

def get_photo_locations(client):
    query = client.query(kind="Photo")
    cursor = None
    locations = []
    while True:
        entities_count = 0
        entities = query.fetch(start_cursor=cursor, limit=1000)
        for entity in entities:
            entities_count += 1
            if entity.has_key('lat') and entity.has_key('lon'):
                # Negate longitude because photo longitude is stored as positive-West, but
                # code needs negative-West.
                location = entity['lat'], -entity['lon']
                locations.append(location)

        if entities_count < 1000:
            break
        cursor = entities.next_page_token
    return locations

def convert_clusters(clusters, locations):
    points = []
    x = []
    y = []
    c = []
    for i, label in enumerate(clusters.labels_):
        x.append(locations[i][0])
        y.append(locations[i][1])

    return x, y

def main():
    args  = get_arguments()

    client = datastore.Client(project=args.project_id)


    locations = get_user_locations(client)

    from sklearn.cluster import DBSCAN
    clusters = cluster_points(locations, eps=0.1, min_samples=10, n_jobs=12)
    centers, sizes = compute_centers(clusters, locations)
    center_points = []
    for center in centers:
        center_points.append(centers[center])
    center_points = np.array(center_points)
    x, y = convert_clusters(clusters, locations)
    plt.scatter(x, y, color='r')
    plt.scatter(center_points[:,0], center_points[:,1], color='black')
    plt.show()


if __name__ == '__main__':
    main()
