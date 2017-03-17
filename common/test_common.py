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

def _clear_data(client):
    query = client.query(kind='__kind__')
    entities = query.fetch()
    for entity in entities:
        kind = entity.key.name
        # Keys starting with __ are reserved and shouldn't be deleted.
        if not kind.startswith("__"):
          query = client.query(kind=kind)
          query.keys_only()
          entities = query.fetch()
          results = []
          for entity in entities:
              results.append(entity.key)
          client.delete_multi(results)

def _print_data(client):
    print "data:"
    query = client.query(kind='__kind__')
    entities = query.fetch()
    for entity in entities:
        kind = entity.key.name
        query = client.query(kind=kind)
        query.keys_only()
        entities = query.fetch()
        results = []
        for entity in entities:
            results.append(entity.key)
        print kind, results

def _set_user_roles(roles, client, user_hash, set_roles):
    return roles.create_user_role(client, user_hash, set_roles)
