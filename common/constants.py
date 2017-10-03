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

#
# General constants
#
DEFAULT_ERROR_MESSAGE = 'An unknown error occured'

HTTP_OK = 200
HTTP_ERROR = 500
HTTP_OOM = 507
HTTP_ENTITY_TOO_LARGE = 413

HTTP_FILENAME_HEADER = 'X-Filename'

_log_fmt_template = '%(levelname)s:{0}%(asctime)s: %(message)s'
LOG_FMT_M_THREADED = _log_fmt_template.format('%(threadName)s:')
LOG_FMT_S_THREADED = _log_fmt_template.format('')

MB = 1024 * 1024

RETRYS = 5

SERVICE_ACCOUNT_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), 'service_account.json')

#
# Static server constants
#
STATIC_SERVER_PORT = 80

#
# Profile server constants
#
GOOGLE_PLUS_USER_URL = 'https://www.googleapis.com/plus/v1/people/me' \
                     + '?fields=emails/value,displayName,image/url'

GOOGLE_MAPS_SCRIPT_URL = 'https://maps.googleapis.com/maps/api/js?key={0}' \
                       + '&libraries=geometry&callback={1}'

ADMIN_GMAPS_CALLBACK = 'admin.gMapsLoaded'
PROFILE_GMAPS_CALLBACK = 'profile.showMap'

#
# Upload constants
#
FILE_NOT_READY_SUFFIX = '.tmp'

MAX_UPLOAD_SIZE = 128 * MB

UPLOAD_DAEMON_MAX_PROCESSES = 8
UPLOAD_DAEMON_SLEEP_TIME = 1

UPLOAD_DIR = '/pending-uploads'

UPLOAD_SERVER_PORT = 80

# This must not end with a '/' otherwise it will not work with the wsgi
# Dispatcher Middleware
UPLOAD_SERVICE_URL_PREFIX = '/services/upload'

# Image processor constants
#
# TODO: Change these (currently set for local-dev)
IMAGE_PROCESSOR_DAEMON_SLEEP_TIME_S = 10
IMAGE_PROCESSOR_DATA_DIR = "/tmp"

#
# Movie constants
#
# TODO: Change these (currently set for local-dev)
MOVIE_DAEMON_MAX_PROCESSES = 64
MOVIE_DAEMON_SLEEP_TIME_S = 10
MOVIE_MIN_FRAMES = 0
MOVIE_DATA_DIR = "/tmp"
MOVIE_FRAMERATE = "2"
MOVIE_FPATH = "{0}/mov.mp4".format(MOVIE_DATA_DIR)
C_MAP_FPATH = "{0}/map.png".format(MOVIE_DATA_DIR)

# Pipeline stats constants
MIN_PHOTOS_IN_CLUSTER = 100
CLUSTER_RADIUS_KM = 90.0
KM_IN_SINGLE_DEGREE = 111.0
CLUSTER_RADIUS_DEGREES = CLUSTER_RADIUS_KM/KM_IN_SINGLE_DEGREE

#
# Readiness check parameters
#
MEM_STAT_FILE = '/sys/fs/cgroup/memory/memory.stat'
RESIDENT_SET_FIELD = 'rss'
ACTIVE_FILE_FIELD = 'active_file'
INACTIVE_FILE_FIELD = 'inactive_file'

UPLOAD_SERVER_READINESS_FILE = '/health/readiness_status'

# Memory usage tolerances used to compute readiness status. Resources will
# report themselves as ready when their usage is below its max value times
# NOT_READY_TOL. However, resources will still respond to requests if they've
# exceeded NOT_READY_TOL times their max value, only when usage exceeds
# STOP_RESPONDING_TOL times their max value will the resource start rejecting
# requests. This is designed as such to be tolerant to a lag between when a
# not ready status is reported and when requests are rejected. Ideally, users
# should never have their requests rejected, the load balancer should pick up
# on the not ready status and forward the requests elsewhere before usage
# exceeds its max value times STOP_RESPONDING_TOL.
NOT_READY_TOL = 0.70
STOP_RESPONDING_TOL = 0.85

# Written to the readiness file when a given resource is ready
STATUS_READY = 'READY'

# Written to the readiness file when a given resource should begin reporting
# that it is not ready through its readiness probe
STATUS_NOT_READY = 'NOTREADY'

# Written to the readiness file when a given resource should stop responding
# to requests.
STATUS_STOP_RESPONDING = 'STOPRESPONDING'

# Interval at which MEM_STAT_FILE is polled and the corresponding readiness file
# is updated, e.g. UPLOAD_SERVER_READINESS_FILE.
READINESS_UPDATE_INTERVAL = 0.5         # seconds
