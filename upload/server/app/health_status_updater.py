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

import logging
import os
import time

from common import constants as const
from common import config


__name = 'Upload server readiness status updater'


class HealthStatusUpdaterError(Exception):
    pass


def _compute_health_status(resident_set, upload_dir_usage):
    """
    Given populated fields dict, returns health status string.
    """
    rss_not_ready_lim = const.NOT_READY_TOL * config.UPLOAD_SERVER_RSS_MAX_USAGE
    dir_not_ready_lim = const.NOT_READY_TOL * config.PENDING_UPLOADS_MAX_USAGE
    rss_stop_resp_lim = const.STOP_RESPONDING_TOL * \
                        config.UPLOAD_SERVER_RSS_MAX_USAGE
    dir_stop_resp_lim = const.STOP_RESPONDING_TOL * \
                        config.PENDING_UPLOADS_MAX_USAGE

    msg = '{0}: RAM usage: {1} File usage: {2}'.format(
        __name, resident_set, upload_dir_usage)
    logging.debug(msg)

    if resident_set < rss_not_ready_lim and \
       upload_dir_usage < dir_not_ready_lim:
        return const.STATUS_READY

    if resident_set < rss_stop_resp_lim and \
       upload_dir_usage < dir_stop_resp_lim:
        return const.STATUS_NOT_READY

    return const.STATUS_STOP_RESPONDING


def _read_usage_data():
    """
    Reads memory usage data and populates fields dict with values for tracked
    metrics.
    """
    # Read the file to obtain rss stat
    try:
        with open(const.MEM_STAT_FILE) as f:
            # Strip off newline characters
            lines = [l.strip() for l in f.readlines()]
    except IOError as e:
        msg = '{0} failed to open {1}. Error: {2}'.format(
            __name, const.MEM_STAT_FILE, e)
        raise HealthStatusUpdaterError(msg)

    # Extract the rss stat
    try:
        # Lines are of the form "<metric_name> <value>", we want <value>
        rss_line = [l for l in lines
                    if l.split()[0] == const.RESIDENT_SET_FIELD][0]
        rss_usage = int(rss_line.split()[1])
    except (IndexError, ValueError) as e:
        msg = '{0} error parsing {1} for rss value. Error: {2}'.format(
            __name, lines, e)
        raise HealthStatusUpdaterError(msg)

    # Compute size of pending uploads directory
    pending_uploads_usage = 0
    try:
        for fname in os.listdir(const.UPLOAD_DIR):
            fpath = os.path.join(const.UPLOAD_DIR, fname)
            pending_uploads_usage += os.path.getsize(fpath)
    except OSError as e:
        msg = '{0} error obtaining size of {1} dir: {2}'.format(
            __name, const.UPLOAD_DIR, e)
        raise HealthStatusUpdaterError(msg)

    return rss_usage, pending_uploads_usage


def _record_status(status):
    """
    Records readiness status.
    """
    try:
        with open(const.UPLOAD_SERVER_READINESS_FILE, 'w') as f:
            f.write(status)
    except IOError:
        msg = '{0} failed to open {1}'.format(
            __name, const.UPLOAD_SERVER_READINESS_FILE)
        logging.error(msg)
        return


def _update_readiness_status():
    """
    Updates the readiness status.
    """
    try:
        rss_usage, pending_uploads_usage = _read_usage_data()
    except HealthStatusUpdaterError as e:
        logging.error(str(e))
        return
    status = _compute_health_status(rss_usage, pending_uploads_usage)
    _record_status(status)


def main():
    logging.basicConfig(level=logging.INFO, format=const.LOG_FMT_S_THREADED)

    while True:
        _update_readiness_status()
        time.sleep(const.READINESS_UPDATE_INTERVAL)


if __name__ == '__main__':
    main()
