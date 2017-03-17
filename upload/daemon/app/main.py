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

from common import config, constants
from common.eclipse2017_exceptions import FailedToUploadToGCSError
import common.service_account as sa

import uploader


# Used when running locally
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = constants.SERVICE_ACCOUNT_PATH


def file_ready(fpath):
    return not fpath.endswith(constants.FILE_NOT_READY_SUFFIX)


def main(sleep_time=constants.UPLOAD_DAEMON_SLEEP_TIME):

    logging.basicConfig(level=logging.INFO,
                        format=constants.LOG_FMT_S_THREADED)

    while True:
        # Scan for files to upload
        fpaths = uploader.scan(constants.UPLOAD_DIR, file_ready=file_ready)

        if len(fpaths) > 0:
            # Upload files
            errors = uploader.upload(fpaths)

            # Attempt to heal any errors that may have occured
            uploader.heal(errors)

        # Allow some files to accumulate before taking our next pass
        time.sleep(sleep_time)


if __name__ == '__main__':
    main()
