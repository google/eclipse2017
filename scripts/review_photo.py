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

"""Make authenticated requests to photo backend."""

import functools
import multiprocessing
import argparse
import json
import os
import requests

from common.id_token import get_id_token

import requests
import logging

import httplib as http_client

def get_arguments():
    parser = argparse.ArgumentParser(description='Make authenticated requests to photo backend')
    parser.add_argument('--debug', type=bool, default=False)
    parser.add_argument('--hostname', type=str, default="localhost")
    parser.add_argument('--photo_id', type=str)
    parser.add_argument('--vote', type=str)
    return parser.parse_args()

def get_photos(id_token, args):
    headers =  { 'x-idtoken': id_token, 'content-type': 'application/json' }
    url = 'https://%s/services/photo/%s' % (args.hostname, args.photo_id)
    data = {
        'vote': args.vote,
        }
    r = requests.patch(url, headers=headers, data=json.dumps(data), verify=False)
    print r
    print r.text


def main():
    args  = get_arguments()
    if args.debug:
        http_client.HTTPConnection.debuglevel = 1
        logging.basicConfig()
        logging.getLogger().setLevel(logging.DEBUG)
        requests_log = logging.getLogger("requests.packages.urllib3")
        requests_log.setLevel(logging.DEBUG)
        requests_log.propagate = True

    id_token = get_id_token()
    r = get_photos(id_token, args)


if __name__ == '__main__':
    main()
