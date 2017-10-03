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
"""Add user."""

import argparse
import json
import os
import requests

from common.id_token import get_id_token

def get_arguments():
    parser = argparse.ArgumentParser(description='Add a user')
    parser.add_argument('--hostname', type=str, default="localhost")
    return parser.parse_args()


def inspect_user_clusters(id_token, args):
    headers =  { 'x-idtoken': id_token }
    url = 'https://%s/services/admin/clusters/users' % args.hostname
    r = requests.get(url, headers=headers, verify=False)

    return r

def inspect_photo_clusters(id_token, args):
    headers =  { 'x-idtoken': id_token }
    url = 'https://%s/services/admin/clusters/photos' % args.hostname
    r = requests.get(url, headers=headers, verify=False)

    return r


def main():
    args  = get_arguments()
    id_token = get_id_token()
    r = inspect_user_clusters(id_token, args)
    print r
    print r.text
    r = inspect_photo_clusters(id_token, args)
    print r
    print r.text

if __name__ == '__main__':
    main()
