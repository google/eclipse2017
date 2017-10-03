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

import copy
import logging
import httplib
import Queue
import socket
import threading
import time

from common import constants


class UploadServerStressTest(object):
    """
    Stress test for upload server. Verifies that upload server behaves correctly
    under heavy load and does not crash. Tests behavior of a single pod.
    """
    HOST = 'localhost'
    READINESS_PROBE_PATH = constants.UPLOAD_SERVICE_URL_PREFIX + '/ready'
    REQUEST_HEADERS = {'content-type': 'text/plain'}

    DATA_FILE_MAX_MBYTES = (constants.MAX_UPLOAD_SIZE * 2) / constants.MB

    ACCEPTED_STATUS_CODES = (constants.HTTP_OK, constants.HTTP_OOM,
                             constants.HTTP_ENTITY_TOO_LARGE)
    NUM_THREADS = 7

    def __init__(self, copy=copy, logger=logging, httplib=httplib,
                 Queue=Queue, socket=socket, threading=threading, time=time):
        # Dependency Injection
        self.copy = copy
        self.logger = logger
        self.httplib = httplib
        self.Queue = Queue
        self.socket = socket
        self.threading = threading
        self.time = time

        self.name = 'Upload server stress test'

        self._retrys = 5
        self._testpass = True
        self._timeout = 5
        self._upload_queue = self.Queue.Queue()
        self._mb_data = ''.join(['a' for _ in range(constants.MB)])
        self._data = dict()
        self._uploads_were_rejected_oom = False

        num_mbytes = 1
        while num_mbytes < (self.DATA_FILE_MAX_MBYTES + 1):
            self._data[num_mbytes] = self._get_some_data(num_mbytes)
            for _ in range(5):
                self._upload_queue.put(num_mbytes)
            num_mbytes *= 2

    def run_when_ready(self):
        """
        Run tests once system under test is online.
        """
        self._wait_until_ready()
        testpass = self._test()

        pass_msg = 'PASS' if testpass else 'FAIL'
        self.logger.info('Test complete. {}.'.format(pass_msg))

        return testpass

    def _check_http_status(self, path):
        """
        Checks the response code of making a request to path on the upload.
        Returns the response code of the request.
        """
        conn = self.httplib.HTTPConnection(self.HOST,
                                           constants.UPLOAD_SERVER_PORT)

        try:
            conn.request('GET', path)
            r = conn.getresponse()

        except (self.httplib.HTTPException, self.socket.error) as e:
            msg = 'Could not make GET request to {0}: {1}'.format(path, repr(e))
            self.logger.error(msg)
            return None

        return r.status

    def _get_some_data(self, num_mbytes):
        """
        Returns a string eith num_mbytes worth of data.
        """
        return ''.join([self._mb_data for _ in range(num_mbytes)])

    def _test(self):
        """
        Run the test. Creates NUM_THREADS which each upload files to the upload
        server.
        """
        self.logger.info('Running test...')

        threads = [self.threading.Thread(target=self._upload_files)
                   for _ in range(self.NUM_THREADS)]

        # Start threads
        for t in threads:
            t.start()

        # Wait for them to finish
        for t in threads:
            t.join()

        # Test is designed such that uploads should be rejected on the basis
        # of the pending uploads directory getting too full, since the upload
        # daemon is disabled for this test
        self._testpass = (self._testpass and self._uploads_were_rejected_oom)

        self.logger.info('Done.')
        return self._testpass

    def _upload_files(self):
        """
        Method called by individual threads to upload files. Pulls files
        from queue and uploads them. If server is down, it sets _testpass to
        False and returns.
        """
        while True:
            try:
                num_mbytes = self._upload_queue.get(block=False)
            except self.Queue.Empty:
                return

            self.logger.info('Uploading {0} MB file...'.format(num_mbytes))

            data = self._data[num_mbytes]
            filename = '{0}_mb_file.txt'.format(num_mbytes)

            headers = self.copy.deepcopy(self.REQUEST_HEADERS)
            headers['X-Filename'] = filename

            conn = self.httplib.HTTPConnection(self.HOST, 
                                               constants.UPLOAD_SERVER_PORT)
            try:
                conn.request('POST', constants.UPLOAD_SERVICE_URL_PREFIX + '/',
                             data, headers)
            except self.socket.error:
                pass

            try:
                r = conn.getresponse()
            except (self.httplib.BadStatusLine, self.socket.error) as e:
                msg = 'Server down. Error: {0}'.format(repr(e))
                self.logger.error(msg)
                self._testpass = False
                continue

            if r.status not in self.ACCEPTED_STATUS_CODES:
                msg = '{0} status uploading {1} MB file'.format(
                    r.status, num_mbytes)
                self.logger.error(msg)
                self._testpass = False

            elif r.status == constants.HTTP_OK:
                msg = 'Successfully uploaded {0} MB file.'.format(num_mbytes)
                self.logger.info(msg)

                # Upload should have been rejected
                if num_mbytes > constants.MAX_UPLOAD_SIZE:
                    self._testpass = False

            else:
                msg = 'Server rejected {0} MB file with status {1}.'.format(
                    num_mbytes, r.status)
                self.logger.info(msg)

                if r.status == constants.HTTP_OOM:
                    self._uploads_were_rejected_oom = True

    def _wait_until_ready(self):
        """
        Blocks until the system under test is online and ready.
        """
        self.logger.info('Waiting for system under test to come online...')

        # Wait until readiness probe responds as ready since newly deployed
        # containers may not be ready yet
        while not (self._check_http_status(self.READINESS_PROBE_PATH)
                   == constants.HTTP_OK):

            msg = 'Not ready... Waiting {0} seconds.'.format(self._timeout)
            self.logger.info(msg)

            self.time.sleep(self._timeout)
