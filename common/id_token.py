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

import google.auth
import google.auth.transport.requests
import google.oauth2._client

def get_id_token():
    # Only works w/ user credentials
    credentials, _ = google.auth.default()

    request = google.auth.transport.requests.Request()
    response = google.oauth2._client.refresh_grant(
        request, credentials.token_uri, credentials.refresh_token,
        credentials.client_id, credentials.client_secret)

    _, _, _, grant_response = response
    id_token = grant_response['id_token']
    return id_token
