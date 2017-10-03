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
    parser.add_argument('--photo_id', type=str)
    parser.add_argument('--debug', type=bool, default=False)
    parser.add_argument('--hostname', type=str, default="localhost")
    parser.add_argument('--num_reviews_max', type=int)
    parser.add_argument('--mask_reviewer', type=bool)
    parser.add_argument('--image_bucket', type=str)
    parser.add_argument('--user_id', type=str)
    parser.add_argument('--upload_session_id', type=str)
    parser.add_argument('--image_datetime_begin', type=int)
    parser.add_argument('--image_datetime_end', type=int)
    parser.add_argument('--uploaded_date_begin', type=int)
    parser.add_argument('--uploaded_date_end', type=int)
    parser.add_argument('--limit', type=int)
    return parser.parse_args()


def get_photos(id_token, args):
    headers =  { 'x-idtoken': id_token, 'content-type': 'application/json' }
    url = 'https://%s/services/photo/' % args.hostname
    params = {}
    if args.num_reviews_max:
        params['num_reviews_max'] = args.num_reviews_max
    if args.mask_reviewer:
        params['mask_reviewer'] = args.mask_reviewer
    if args.image_bucket:
        params['image_bucket'] = args.image_bucket
    if args.user_id:
        params['user_id'] = args.user_id
    if args.upload_session_id:
        params['upload_session_id'] = args.upload_session_id
    if args.image_datetime_begin:
        params['image_datetime_begin'] = args.image_datetime_begin
    if args.image_datetime_end:
        params['image_datetime_end'] = args.image_datetime_end
    if args.uploaded_date_begin:
        params['uploaded_date_begin'] = args.uploaded_date_begin
    if args.uploaded_date_end:
        params['uploaded_date_end'] = args.uploaded_date_end
    if args.limit:
        params['limit'] = args.limit

    while True:
        r = requests.get(url, headers=headers, params=params, verify=False)
        if r.status_code != 200:
            print "Error:", r.status_code, r.text
            break
        j = r.json()
        for photo in j['photos']:
            print photo
        if j.has_key('cursor'):
            params['cursor'] = j['cursor']
            print
        else:
            break

def get_photo(id_token, args):
    headers =  { 'x-idtoken': id_token, 'content-type': 'application/json' }
    url = 'https://%s/services/photo/%s' % (args.hostname, args.photo_id)
    r = requests.get(url, headers=headers, verify=False)
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
    if args.photo_id is not None:
        get_photo(id_token, args)
    else:
        get_photos(id_token, args)


if __name__ == '__main__':
    main()
