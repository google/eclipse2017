#
# Copyright 2016 Google Inc.
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

import os
import sys
import logging
import itertools

import matplotlib # Force matplotlib to not use any Xwindows backend
matplotlib.use('Agg')
from matplotlib import pyplot as plt

from google.cloud import datastore, storage

from common import datastore_schema as ds
from common import config, constants
from common.cluster_points import cluster_points

from multiprocessing import Pool
from sklearn.preprocessing import StandardScaler
from mpl_toolkits.basemap import Basemap


class Pipeline_Stats():

    def __init__(self, datastore_client, storage_client):
        self.datastore = datastore_client
        self.storage = storage_client

    def get_clusters(self, fnames):
        """
       Returns list of clusters and outliers
        """

        coordinates, fnames = self._get_gps_coordinates(fnames)

        if coordinates:
            clusters =  self._get_clusters(fnames, coordinates)
        else:
            return None

        return clusters

    def _get_clusters(self, fnames, coordinates):
        """
        Returns list of lists of files clustered in a geographic area
        """

        # Get number of clusters and list of labels
        db = cluster_points(coordinates)
        n_clusters, cluster_labels = count_clusters(db, eps=constants.CLUSTER_RADIUS_DEGREES, min_samples=constants.MIN_PHOTOS_IN_CLUSTER, n_jobs=min(len(coordinates), constants.MOVIE_DAEMON_MAX_PROCESSES))

        # Convert labels into list of files grouped by cluster, maintain order within cluster
        clusters = [[] for i in range(n_clusters)]

        for i in range(len(coordinates)):
            cluster_label = cluster_labels[i]
            if cluster_label != -1:
                clusters[cluster_label].append(fnames[i])


        self._create_map(coordinates, cluster_labels, n_clusters)

        return clusters

    def _get_gps_coordinates(self, fnames):
        """
        Function to pull lat/long fields from datastore Photo entities
        """
        coordinates = []
        successful_fnames = []

        # Get Photo entities from datastore
        keys = list(self.datastore.key(ds.DATASTORE_PHOTO, fname) for fname in fnames)

        try:
            entities = self.datastore.get_multi(keys)
        except Exception, e:
            msg = 'Failed to get {0} from Cloud Datastore.'
            logging.exception(msg.format(keys))
            return None


        for entity in entities:
            try:
                coordinates.append((entity['lat'], entity['lon']))
            except Exception, e:
                msg = 'Entity {0} missing {1}'
                logging.error(msg.format(entity, e))
                continue

            successful_fnames.append(entity.key.name)

        return coordinates, successful_fnames


    def _create_map(self, coordinates, labels, n_clusters):
        """
        Graphs GPS coordinates on map (used ti verify clustering algo)
        """
        map = Basemap(llcrnrlat=22, llcrnrlon=-119, urcrnrlat=49, urcrnrlon=-64,
        projection='lcc',lat_1=33,lat_2=45,lon_0=-95)

        base_color = 'white'
        border_color = 'lightgray'
        boundary_color = 'gray'

        map.fillcontinents(color=base_color, lake_color=border_color)
        map.drawstates(color=border_color)
        map.drawcoastlines(color=border_color)
        map.drawcountries(color=border_color)
        map.drawmapboundary(color=boundary_color)


        lat, lon = zip(*coordinates)
        map.scatter(lon, lat, latlon=True, s=1, alpha=0.5, zorder=2)


        plt.title('Estimated number of clusters: %d' % n_clusters)

        #Upload an image to Cloud Storage
        plt.savefig(constants.C_MAP_FPATH)

        if os.path.exists(constants.C_MAP_FPATH):
            print "HERERE"
        else:
            print "NOT HEEEEEEEEEEEEEEEEEEEEEEEEEEEEEERRRRRRRRRRRRRRRRRRREEEEEEEEEEEE"
