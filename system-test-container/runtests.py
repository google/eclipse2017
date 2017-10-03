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
# limitations under the License

import os
import shutil
import subprocess
import sys
import tempfile
import time


NO_ERROR = 0
ERROR = 1

OUTPUT_FILE_PATH = '/dev/null'

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
SERVER_DIR = os.path.join(os.path.dirname(TEST_DIR), 'server')

def _get_test_status():
    kube_cmd = [
        'kubectl',
        'logs',
        'upload',
        '-c',
        'upload-system-tests'
    ]

    print "Waiting for test to complete and retrieving status..."

    while True:
        time.sleep(5)

        f = tempfile.TemporaryFile(mode='w+')
        subprocess.call(kube_cmd, stdout=f)

        f.seek(0)
        output = f.read()
        f.close()

        try:
            idx = output.index('Test complete')
            break
        except ValueError:
            continue

    if 'PASS' in output[idx:]:
        return True, output
    return False, output


def _pull_deployment(output_file):
    kube_cmd = [
        'kubectl',
        'delete',
        'pod',
        'upload'
    ]

    print "Pulling down kubernetes deployment..."

    return _run_cmds((kube_cmd, ), output_file)

def _run_cmds(cmds, output_file):
    for cmd in cmds:
        res = subprocess.call(cmd, stdout=output_file, stderr=output_file)
        if res != NO_ERROR:
            return False
    return True


def main():

    try:
        with open(OUTPUT_FILE_PATH, 'w') as output_file:

            if not _deploy(output_file):
                print 'Failed to deploy upload pod with upload server and test.'
                return ERROR

            status, output = _get_test_status()

            if not _pull_deployment(output_file):
                print 'Failed to pull down upload system tests.'
                return ERROR

            if status is True:
                print 'Test passed'
                exit_code = NO_ERROR
            else:
                print output
                exit_code = ERROR

    except IOError:
        print 'Could not open output file: {0}'.format(OUTPUT_FILE_PATH)
        return ERROR

    return exit_code


if __name__ == '__main__':
    status = main()
    sys.exit(status)
