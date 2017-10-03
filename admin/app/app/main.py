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

import traceback
import logging
import os

from common import constants
from common import config
from common import secret_keys as sk

from backend.eclipse2017_admin_app import Eclipse2017AdminApp

from werkzeug.urls import url_encode

os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = constants.SERVICE_ACCOUNT_PATH

logging.basicConfig(level=logging.INFO, format=constants.LOG_FMT_S_THREADED)

app = Eclipse2017AdminApp(config.PROJECT_ID, sk.FLASK_SESSION_ENC_KEY,
                          sk.GOOGLE_OAUTH2_CLIENT_ID,
                          sk.GOOGLE_OAUTH2_CLIENT_SECRET,
                          debug=False)
# This is a disgusting hacky work-around for the fact that flask looks at the
# url scheme of individual requests before looking at the PREFERRED_URL_SCHEME
# config value. All our requests have an http url scheme as they come as http
# requests from nginx to gunicorn/flask. See more info here:
#   http://stackoverflow.com/questions/34802316/make-flasks-url-for-use-the-https-scheme-in-an-aws-load-balancer-without-mess
def _force_https():
    from flask import _request_ctx_stack
    if _request_ctx_stack is not None:
        reqctx = _request_ctx_stack.top
        reqctx.url_adapter.url_scheme = 'https'

app.before_request(_force_https)

@app.errorhandler(Exception)
def all_exception_handler(error):
    traceback.print_exc()
    logging.error("internal server error: %s" % str(error))
    return 'Internal server error', 500
