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

import time
import argparse
import oauth2client
import urllib
import httplib
from oauth2client import tools
from oauth2client import client
from oauth2client import service_account
from oauth2client.client import OAuth2WebServerFlow
from oauth2client.file import Storage
import json
scopes=[ 'email', 'profile' ]

parser = argparse.ArgumentParser(parents=[tools.argparser])
flags = parser.parse_args()
credentials = client.GoogleCredentials.get_application_default()

now = int(time.time())
payload = {
        'iat': now,
        'exp': now + credentials.MAX_TOKEN_LIFETIME_SECS,
        'aud': 'https://www.googleapis.com/oauth2/v4/token',
        'iss': 'https://accounts.google.com',
        'scope': 'profile'
}

signed_jwt = oauth2client.crypt.make_signed_jwt(credentials._signer, payload, key_id=credentials._private_key_id)
params = urllib.urlencode({
      'grant_type': 'urn:ietf:params:oauth:grant-type:jwt-bearer',
      'assertion': signed_jwt })
headers = {"Content-Type": "application/x-www-form-urlencoded"}
conn = httplib.HTTPSConnection("www.googleapis.com")
conn.request("POST", "/oauth2/v4/token", params, headers)
r = conn.getresponse().read()
print r
res = json.loads(conn.getresponse().read())
print res
import pdb; pdb.set_trace()


# from common import secret_keys as sk
# # CLIENT_SECRETS = 'common/service_account.json'
# # creds= service_account.ServiceAccountCredentials.from_json_keyfile_name(CLIENT_SECRETS, scopes=scopes)
# flow = client.flow_from_clientsecrets(
#         '/var/www/.config/gcloud/application_default_credentials.json',  # downloaded file
#         'https://www.googleapis.com/auth/userinfo.email'  # scope
#         redirect_uri='urn:ietf:wg:oauth:2.0:oob')
# storage = Storage('credentials.dat')
# credentials = tools.run_flow(flow, storage, flags)

# import pdb; pdb.set_trace()
# flow = client.OAuth2WebServerFlow(sk.GOOGLE_OAUTH2_CLIENT_ID,
#                                   sk.GOOGLE_OAUTH2_CLIENT_SECRET, scopes)


# http = httplib2.Http()
# http = credentials.authorize(http)
