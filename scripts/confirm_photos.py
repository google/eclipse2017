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

"""Confirms photos (debug tool)."""

import logging
import argparse
import requests
import json
from common.id_token import get_id_token
import httplib as http_client

# This is not a valid project name (for safety)
DEFAULT_PROJECT = 'eclipse-2017-test'

def get_arguments():
    parser = argparse.ArgumentParser(description='Confirm photos.')
    parser.add_argument('--project_id', type=str, default=DEFAULT_PROJECT)
    parser.add_argument('--debug', type=bool, default=False)
    parser.add_argument('--hostname', type=str, default="localhost")
    parser.add_argument('--upload_session_id', type=str)
    parser.add_argument('--filename', type=str) # use one --filename per file
    return parser.parse_args()

def confirm_photos(id_token, args):
    if args.debug:
        http_client.HTTPConnection.debuglevel = 1
        logging.basicConfig()
        logging.getLogger().setLevel(logging.DEBUG)
        requests_log = logging.getLogger("requests.packages.urllib3")
        requests_log.setLevel(logging.DEBUG)
        requests_log.propagate = True

    headers =  { 'x-idtoken': id_token, 'content-type': 'application/json' }
    url = 'https://%s/services/photo/confirm' % args.hostname
    data = {
        'upload_session_id': args.upload_session_id,
        'filenames': args.filename
        }
    r = requests.post(url, headers=headers, data=json.dumps(data), verify=False)
    print r
    print r.text

def main():
    args  = get_arguments()
    id_token = get_id_token()
    r = confirm_photos(id_token, args)

if __name__ == '__main__':
    main()
