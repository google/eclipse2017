
import pytz
import datetime

# Criteria for photo inclusion:
# 1) Must be megamovie or teramovie photo
# 2) Must be confirmed by user
# 3) Must not be adult content
# 4) Must not be (administratively) blacklisted
# 5) Must have (possibly imputed) lat, lon, and image_datetime
# 6) User must have agreed for photo to be public
# 7) User must have agreed to license assignment
# 8) Must have been taken on Eclipse Day
def filter_photo_record(entity, debug=False):
    if not entity.has_key("original_filename"):
        if debug: print "entity mising original_filename"
        return False

    fname = entity['original_filename']

    if not entity.has_key('user'):
        if debug: print "image is missing user"
        return False

    if not entity.has_key('image_bucket'):
        if debug: print "image is missing image bucket"
        return False

    if entity['image_bucket'] != 'megamovie' and entity['image_bucket'] != 'teramovie':
        if debug: print "image bucket must be megamovie or teramovie"
        return False

    if not entity['confirmed_by_user'] == True:
        if debug: print "user did not confirm image"
        return False

    if entity.has_key('is_adult_content') and entity['is_adult_content'] == True:
        if debug: print "picture is adult content"
        return False

    if entity['in_gcs'] == False:
        if debug: print "picture is not in GCS"
        return False

    if entity.has_key('blacklisted') and entity['blacklisted'] is True:
        if debug: print "blacklisted image", entity.key.name
        return False

    if not entity.has_key('lat') or not entity.has_key('lon'):
        if debug: print "image", entity.key.name, "is missing critical info (lat, lon)"
        return False

    if not entity.has_key('image_datetime'):
        if debug: print "image", entity.key.name, "is missing critical info (datetime)"
        return False

    public_agree = entity.get('public_agree', None)
    if public_agree == None:
        if debug: print "image", entity.key.name, "is missing public_agree"
        return False
    if public_agree != 'True' and public_agree != 'true':
        if debug: print "image", entity.key.name, "public_agree is not true:", public_agree
        return False

    cc0_agree = entity.get('cc0_agree', None)
    if cc0_agree == None:
        if debug: print "image", entity.key.name, "is missing cc0_agree"
        return False
    if cc0_agree != 'True' and cc0_agree != 'true':
        if debug: print "image", entity.key.name, "cc0_agree is not true:", cc0_agree
        return False

    equatorial_mount = entity.get('equatorial_mount', None)
    if not entity.has_key('equatorial_mount'):
        if debug: print "image lacks equatorial mount field"
        return False

    if entity['image_datetime'] < datetime.datetime(2017, 8, 21, 0, 0, 0, 0, pytz.UTC):
        if debug: print "image", entity.key.name, "too old", entity['image_datetime']
        return False
    if entity['image_datetime'] > datetime.datetime(2017, 8, 22, 0, 0, 0, 0, pytz.UTC):
        if debug: print "image", entity.key.name, "too new", entity['image_datetime']
        return False

    return True
