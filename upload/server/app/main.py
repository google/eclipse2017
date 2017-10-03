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

import logging
import os

import flask
from werkzeug import wsgi

from common import config, constants
from common import datastore_schema as ds
from common import secret_keys as sk

from backend.upload_server import UploadServer


service_account_path = os.path.abspath('./common/service_account.json')
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = service_account_path

logging.basicConfig(level=logging.INFO,
                    format=constants.LOG_FMT_M_THREADED)

upload_server = UploadServer(
    config.PROJECT_ID,
    sk.FLASK_SESSION_ENC_KEY,
    sk.GOOGLE_OAUTH2_CLIENT_ID,
    sk.GOOGLE_OAUTH2_CLIENT_SECRET,
    file_not_ready_suffix=constants.FILE_NOT_READY_SUFFIX,
    directory=constants.UPLOAD_DIR,
    datastore_kind=ds.DATASTORE_PHOTO,
    user_datastore_kind=ds.DATASTORE_USER,
    retrys=constants.RETRYS)

# Set up the app so that all it's routes live under the /upload url prefix
# A dummy no-op flask app is used for all other routes, so they will result in
# a 404 not found error.
app = wsgi.DispatcherMiddleware(flask.Flask('nop'),
                                {constants.UPLOAD_SERVICE_URL_PREFIX: upload_server})
