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

import functools
import multiprocessing
import argparse
import json
import os
import requests

from common.id_token import get_id_token

def get_arguments():
    parser = argparse.ArgumentParser(description='Add a user')
    parser.add_argument('--hostname', type=str, default="localhost")
    parser.add_argument('--user_id', type=str)
    parser.add_argument('--name', type=str)
    parser.add_argument('--email', type=str)
    return parser.parse_args()


def create_user(id_token, args):
    headers =  { 'x-idtoken': id_token, 'content-type': 'application/json' }
    url = 'https://%s/services/user/profile/%s' % (args.hostname, args.user_id)
    data = json.dumps({ 'name': args.name, 'email': args.email })
    r = requests.put(url, headers=headers, data=data, verify=False)

    return r


def main():
    args  = get_arguments()
    id_token = get_id_token()
    r = create_user(id_token, args)
    print r.text


if __name__ == '__main__':
    main()
