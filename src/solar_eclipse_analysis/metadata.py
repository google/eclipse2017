import pytz
import datetime

def get_metadata(entity, image_bucket, debug=False):
    if not entity.has_key("original_filename"):
        if debug: print "entity mising original_filename"
        return None

    fname = entity['original_filename']

    if not entity.has_key('user'):
        if debug: print "image is missing user"
        return None
    
    if not entity['image_bucket'] == image_bucket:
        if debug: print "image bucket is not a match: ", image_bucket
        return None

    if not entity['confirmed_by_user'] == True:
        if debug: print "user did not confirm image"
        return None

    if entity.has_key('is_adult_content') and entity['is_adult_content'] == True:
        if debug: print "picture is adult content"
        return None

    if entity['in_gcs'] == False:
        if debug: print "picture is not in GCS"
        return None

    if entity.has_key('blacklisted') and entity['blacklisted'] is True:
        if debug: print "blacklisted image", entity.key.name
        return None

    if not entity.has_key('lat') or not entity.has_key('lon'):
        if debug: print "image", entity.key.name, "is missing critical info (lat, lon)"
        return None

    if not entity.has_key('image_datetime'):
        if debug: print "image", entity.key.name, "is missing critical info (datetime)"
        return None

    public_agree = entity.get('public_agree', None)
    if public_agree == None:
        if debug: print "image", entity.key.name, "is missing public_agree"
        return None
    if public_agree != 'True' and public_agree != 'true':
        if debug: print "image", entity.key.name, "public_agree is not true:", public_agree
        return None

    cc0_agree = entity.get('cc0_agree', None)
    if cc0_agree == None:
        if debug: print "image", entity.key.name, "is missing cc0_agree"
        return None
    if cc0_agree != 'True' and cc0_agree != 'true':
        if debug: print "image", entity.key.name, "cc0_agree is not true:", cc0_agree
        return None

    equatorial_mount = entity.get('equatorial_mount', None)
    if not entity.has_key('equatorial_mount'):
        if debug: print "image lacks equatorial mount field"
        return None

    metadata = {}
    if entity['image_datetime'] < datetime.datetime(2017, 8, 21, 0, 0, 0, 0, pytz.UTC):
        if debug: print "image", entity.key.name, "too old", entity['image_datetime']
        return None
    if entity['image_datetime'] > datetime.datetime(2017, 8, 22, 0, 0, 0, 0, pytz.UTC):
        if debug: print "image", entity.key.name, "too new", entity['image_datetime']
        return None

    for key in [u'image_datetime', u'equatorial_mount', u'lon', u'lat', 'width', 'height', 'user']:
        if key in entity:
            metadata[key] = entity[key]
    return metadata
