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
import sys
import traceback
from common import config, constants
from common.eclipse2017_exceptions import FailedToUploadToGCSError
import common.service_account as sa
from common.chunks import chunks

import uploader


# Used when running locally
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = constants.SERVICE_ACCOUNT_PATH


def file_ready(fpath):
    return not fpath.endswith(constants.FILE_NOT_READY_SUFFIX)

def main(sleep_time=constants.UPLOAD_DAEMON_SLEEP_TIME):

    logging.basicConfig(level=logging.INFO,
                        format=constants.LOG_FMT_S_THREADED)
    logging.info("Upload daemon copying files to gs://" + config.GCS_BUCKET)
    while True:
        try:
          logging.debug("Scanning for files to upload")
          # Scan for files to upload
          fpaths = uploader.scan(constants.UPLOAD_DIR, file_ready=file_ready)

          if len(fpaths) > 0:
              # Upload files
              logging.debug("Uploading files: " + str(fpaths))
              # Never upload more than 1000 files in a group, as the
              # code that updates datastore can't handle more than
              # 1000 entries in a single call.
              for group in list(chunks(fpaths, 1000)):
                  logging.debug("Uploading group of files: " + str(group))
                  errors = uploader.upload(group)

                  # Attempt to heal any errors that may have occured
                  logging.info("Healing errors: " + str(errors))
                  uploader.heal(errors)
        except Exception as e:
            logging.error("Unexpected exception caught at uploader outer loop:" + str(e))
            ex_type, ex, tb = sys.exc_info()
            traceback.print_tb(tb)

        # Allow some files to accumulate before taking our next pass
        time.sleep(sleep_time)


if __name__ == '__main__':
    main()
