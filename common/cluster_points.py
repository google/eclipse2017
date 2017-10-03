from sklearn.cluster import DBSCAN
from common import constants
import numpy as np

def cluster_points(coordinates, eps, min_samples, n_jobs=1):
    """Given coordinates, function returns the number of clusters in the
    set of coordinates and a list of integer labels corresponding to
    the input coordinate list

    Arguments:
      coordinates: a sequence of (lat, lon) tuples
      eps: the cluster size in radial degrees
      min_samples: the size of the smallest cluster
      n_jobs: number of CPUs to use to compute the clusters
    Returns:
      n_clusters: number of clusters
      labels: the labels of the clusters
    """

    db = DBSCAN(eps=eps,
                min_samples=min_samples,
                n_jobs=n_jobs).fit(coordinates)


    return db

def count_clusters(db):
    labels = db.labels_
    n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
    return (n_clusters, labels)

def compute_centers(clusters, locations, suppress_negative=True):
    """Compute centroids of clusters.

    Arguments:
      clusters: sklearn cluster object with labels_ attribute
      locations: the x,y coordinates of the items
      suppress_negative: if True, will suppress any cluster label which is -1.  -1 means "not assigned to a cluster".

    Returns:
      centers: dictionary of label -> centroids
      sizes: dictionary of label -> the sizes of the centroid (number of members)
    """

    points = {}
    print clusters
    for i, label in enumerate(clusters.labels_):
        if suppress_negative and label == -1:
            continue
        if label not in points:
            points[label] = []
        points[label].append( (locations[i][0], locations[i][1]))

    centers = {}
    sizes = {}
    for label in points:
        centers[label] = np.mean(points[label], axis=0)
        sizes[label] = len(points[label])

    return centers, sizes
