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

"""Update roles for a user."""

import argparse
from gcloud import datastore

DEFAULT_PROJECT = 'eclipse-2017-test'
INVALID_USER = '-1'

def get_arguments():
    parser = argparse.ArgumentParser(description='Update roles for a user.')
    parser.add_argument('--project_id', type=str, default=DEFAULT_PROJECT,
                        help = 'Project ID to apply updates to')
    parser.add_argument('--user_id', type=str, default=INVALID_USER,
                        help = 'User ID to apply updates to')
    parser.add_argument('--add_roles', nargs='+', type=str, default = [],
                        help = 'Roles to add to user')
    parser.add_argument('--remove_roles', nargs='+', type=str, default = [],
                        help = 'Roles to remove from user')
    return parser.parse_args()

def main():
    args  = get_arguments()

    client = datastore.Client(args.project_id)

    key = client.key("UserRole", args.user_id)
    entity = client.get(key)

    if entity:
        roles = set(entity['roles'])
        print "original roles:", roles
        for role in args.add_roles:
            roles.add(unicode(role, 'utf8'))
        for role in args.remove_roles:
            if role in roles:
                roles.remove(unicode(role, 'utf8'))

        roles = list(roles)
        print "new roles:", roles
        entity['roles'] = roles
        client.put(entity)
    else:
        print "No such user:", args.user_id


if __name__ == '__main__':
    main()
