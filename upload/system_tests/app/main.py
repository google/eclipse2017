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
import time

from common import constants

from tests.upload_server_stress_test import UploadServerStressTest


logging.basicConfig(level=logging.INFO, format=constants.LOG_FMT_M_THREADED)

TESTS = (
    (UploadServerStressTest, [], {'logger': logging}),
)


def main():

    for test_cls, args, kwargs in TESTS:

        test = test_cls(*args, **kwargs)
        res = test.run_when_ready()

        # Loop forever. Otherwise kubernetes will restart the container
        while True: time.sleep(1000)


if __name__ == '__main__':
    main()
