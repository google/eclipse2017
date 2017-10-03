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


import cgi
import types
import hashlib

from common.secret_keys import GOOGLE_HTTP_API_KEY, GOOGLE_OAUTH2_CLIENT_ID
from google.oauth2 import id_token
from google.auth.transport import requests
from common.eclipse2017_exceptions import ApplicationIdentityError

request = requests.Request()

def in_list(lst, val, key=None):
    """
    Searches for val in lst. If specified, key will be applied to each element
    in lst before comparing it to val.
    """
    if key is None:
        return val in lst

    for elem in lst:
        if key(elem) == val:
            return True

    return False


def retry_func(func, retrys, allowed_exceptions, *args, **kwargs):
    """
    Calls `func` with `args` and `kwargs` until it executes without raising an
    exception in `allowed_exceptions`. Calls a max of `retrys` times.
    Returns the return value of `func` call. If func raises an exception not in
    `allowed_exceptions` or raises an exception in `allowed_exceptions` on
    every execution, RuntimeError is raised.

    Example call:
    ```
    try:
        retry_func(os.remove, 2, (OSError, ), '/some/file/to.remove')
    except RuntimeError:
        print 'Could not remove file'
    ```
    """
    for _ in range(retrys):
        try:
            return func(*args, **kwargs)
        except allowed_exceptions:
            pass
        except BaseException as e:
            msg = '{0} raised executing {1}'.format(e, func.__name__)
            raise RuntimeError(msg)
    raise RuntimeError('Failed to execute {0}'.format(func.__name__))


def _escape_json(json):
    """Escapes all string fields of JSON data.

       Operates recursively."""
    t = type(json)
    if t == types.StringType or t == types.UnicodeType:
        return cgi.escape(json)
    elif t == types.IntType:
        return json
    elif t == types.FloatType:
        return json
    elif t == types.DictType:
        result = {}
        for f in json.keys():
            result[f] = _escape_json(json[f])
        return result
    elif t == types.ListType:
        result = []
        for f in json:
            result.append(_escape_json(f))
        return result
    else:
        raise RuntimeError, "Unsupported type: %s" % str(t)

class MisformattedInputError(Exception):
    pass

class MissingInputError(Exception):
    pass

def _validate_json(request):
    """If JSON input is valid, return True.  If not, immediately fail the
       request."""
    try:
        json = request.get_json()
    except ValueError as e:
        raise MisformattedInputError

    if json == None:
        raise MissingInputError

    return True

def _update_entity(json, ALL_FIELDS, entity):
    for field in ALL_FIELDS:
        if field in json:
            entity[field] = json[field]
    return entity

def _validate_id_token(token):
    idinfo = id_token.verify_token(token, request)
    if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
        raise ApplicationIdentityError
    ## TODO(dek): implement additional checks from the Google OAuth examples server-side example page
    return idinfo
