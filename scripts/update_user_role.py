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
from google.cloud import datastore

DEFAULT_PROJECT = 'eclipse-2017-test'

def get_arguments():
    parser = argparse.ArgumentParser(description='Update roles for a user.')
    parser.add_argument('--project_id', type=str, default=DEFAULT_PROJECT,
                        help = 'Project ID to apply updates to')
    parser.add_argument('--user_id_file', type=str,
                        help = 'File of user ids to apply updates to (combined with --user_id)')
    parser.add_argument('--user_id', type=str,
                        help = 'Single user id to apply updates to (combined with --user_id_file)')
    parser.add_argument('--add_roles', nargs='+', type=str, default = [],
                        help = 'Roles to add to user')
    parser.add_argument('--remove_roles', nargs='+', type=str, default = [],
                        help = 'Roles to remove from user')
    return parser.parse_args()

def main():
    args  = get_arguments()

    client = datastore.Client(args.project_id)

    user_ids = []
    if args.user_id_file:
        f = open(args.user_id_file)
        user_ids.extend([line.strip() for line in f.readlines()])
    if args.user_id:
        user_ids.append(args.user_id)

    for user_id in user_ids:
        key = client.key("UserRole", user_id)
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
            print "No such user:", user_id


if __name__ == '__main__':
    main()
