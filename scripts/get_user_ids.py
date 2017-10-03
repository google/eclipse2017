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

"""Print user ids matching email addresses."""

import argparse
from google.cloud import datastore
import common.service_account as sa

DEFAULT_PROJECT_ID = 'eclipse-2017-test-147301'
DEFAULT_EMAIL_ADDRESS_FILE = 'email_addresses.txt'

def get_arguments():
    parser = argparse.ArgumentParser(description='Print user ids matching email addresses.')
    parser.add_argument('--project_id', type=str, default=DEFAULT_PROJECT_ID)
    parser.add_argument('--email_address_file', type=str, default=DEFAULT_EMAIL_ADDRESS_FILE)
    return parser.parse_args()

def main():
    args  = get_arguments()

    client = datastore.Client(project=args.project_id)

    addresses = [address.strip() for address in open(args.email_address_file).readlines()]
    # Can't find a way to query a collection of records matching different email addresses.
    for email in addresses:
        query = client.query(kind="User")
        query.add_filter('email', '=', email)
        entities = query.fetch()
        l = list(entities)
        if l == []:
            print "No match for", email
        else:
            for entity in l:
                print entity.key.name, entity['email']

if __name__ == '__main__':
    main()
