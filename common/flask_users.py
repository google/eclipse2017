from common.eclipse2017_exceptions import MissingCredentialTokenError, MissingUserError, ApplicationIdentityError
from common import util
from common import users
import flask

def authn_check(headers):
    try:
        token = users.get_id_token(headers)
    except MissingCredentialTokenError:
        return flask.Response("The request is missing a credential token.", 405)
    try:
        idinfo = util._validate_id_token(token)
    except ApplicationIdentityError:
        return flask.Response("The request id token is invalid.", 405)
    except ValueError:
        return flask.Response("The request id token is expired.", 401)
    try:
        userid = users.get_userid(idinfo)
    except MissingUserError:
        return flask.Response("The user is missing.", 405)
    return userid
