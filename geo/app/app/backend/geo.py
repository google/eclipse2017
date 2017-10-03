
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
import datetime
import googlemaps
import logging
from common.secret_keys import GOOGLE_MAPS_API_KEY

from app_module import AppModule

# googlemaps API timeouts
TIMEOUT=10
RETRY_TIMEOUT=20

class Geo(AppModule):
    """
    Class for geo timezone lookups.
    """
    def __init__(self, **kwargs):
        super(Geo, self).__init__(**kwargs)

        self.name = 'geo'
        self.import_name = __name__

        self._routes = (
            ('/', 'root', self.root, ('GET',)),
            ('/timezone', 'timezone', self.timezone, ('GET',)))

        self.gmaps = googlemaps.Client(key=GOOGLE_MAPS_API_KEY,
                                       timeout=TIMEOUT,
                                       retry_timeout=RETRY_TIMEOUT)

    def root(self):
        return flask.Response('OK', status=200)

    def timezone(self):
        location = flask.request.args.get('location')
        timestamp = flask.request.args.get('timestamp')
        try:
            tz = self.gmaps.timezone(location=location, timestamp = timestamp)
        except googlemaps.exceptions.Timeout:
            return flask.Response('Timeout exceeded', status=408)
        except googlemaps.exceptions.ApiError:
            return flask.Response('API error', status=400)
        except googlemaps.exceptions.TransportError:
            return flask.Response('Transport error', status=500)
        except Exception as e:
            logging.error("Unhandled Exception, location: %s, timestamp: %s" % (str(location), str(timestamp)))
            return flask.Response('Internal server error', status=500)
        else:
            return flask.jsonify(tz)

geo = Geo()
