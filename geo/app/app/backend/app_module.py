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

import datetime
import json

import flask
from google.cloud import datastore



class AppModule(object):
    """
    Base class for application module
    """
    def __init__(self, Blueprint=flask.Blueprint, current_app=flask.current_app,
                 redirect=flask.redirect, render_template=flask.render_template,
                 request=flask.request, Response=flask.Response,
                 session=flask.session, url_for=flask.url_for,
                 datastore=datastore, datetime=datetime.datetime, json=json):
        # Dependency injection
        self.Blueprint = Blueprint
        self.current_app = current_app
        self.redirect = redirect
        self.render_template = render_template
        self.request = request
        self.Response = Response
        self.session = session
        self.url_for = url_for
        self.datastore = datastore
        self.datetime = datetime
        self.json = json

        self.name = 'appmodule'
        self.import_name = __name__
        self._routes = None

    def create_blueprint(self):
        """
        Creates and returns a flask blueprint for the geo module.
        """
        bp = self.Blueprint(self.name, self.import_name)

        for route, name, method, rest_methods in self._routes:
            bp.add_url_rule(route, name, method, methods=rest_methods)

        return bp

    def _get_datastore_client(self):
        """
        Returns a datastore client.
        """
        return self.datastore.Client(self.current_app.config['PROJECT_ID'])
