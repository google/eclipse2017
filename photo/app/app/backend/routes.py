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

import flask

class Routes(object):
    """
    Class with base route definitions, responsible for registration of base
    routes and additional module blueprints.
    """
    def __init__(self, redirect=flask.redirect,
                 render_template=flask.render_template, request=flask.request,
                 Response=flask.Response, session=flask.session,
                 url_for=flask.url_for):
        # Dependency injection
        self.redirect = redirect
        self.render_template = render_template
        self.request = request
        self.Response = Response
        self.session = session
        self.url_for = url_for

        # Define routes within this class, all routes from this class have
        # no prefix
        self._routes = (
            ('/', 'index', self.health_check),
            ('/healthz', 'heathz', self.health_check))

    # TODO make this useful
    def health_check(self):
        """
        Health check for GKE.
        """
        return self.Response('OK', status=200)

    def register(self, app, blueprints):
        """
        Define standard routes and register module blueprints.
        """

        for path, name, method in self._routes:
            app.add_url_rule(path, name, method)

        for bp, url_prefix in blueprints:
            app.register_blueprint(bp, url_prefix=url_prefix)
