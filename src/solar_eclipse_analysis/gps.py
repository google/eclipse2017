import string
from geometry import ratio_to_decimal
import datetime
import logging
def _convert_gps_to_degrees(gps):
    gps_ratios = gps.split(", ")
    if len(gps_ratios) != 3:
        return None
    gps_ratio_h = gps_ratios[0].split("/")
    if len(gps_ratio_h) != 2:
        return None
    gps_ratio_m = gps_ratios[1].split("/")
    if len(gps_ratio_m) != 2:
        return None
    gps_ratio_s = gps_ratios[2].split("/")
    if len(gps_ratio_s) != 2:
        return None
    try:
        gps_h = int(gps_ratio_h[0]) / float(gps_ratio_h[1])
        gps_m = int(gps_ratio_m[0]) / float(gps_ratio_m[1])
        gps_s = int(gps_ratio_s[0]) / float(gps_ratio_s[1])
    except:
        return None
    deg = gps_h + gps_m/60. + gps_s / 3600.
    return deg
def exifread_tags_to_latlon(tags):
    try:
        if tags.has_key('GPS GPSLatitude'):
            lat = hms_to_deg(tags['GPS GPSLatitude'])
            if lat is not None:
              lat_ref = tags.get('GPS GPSLatitudeRef')
              if lat_ref == 'S':
                  lat = -lat
        else:
            lat = None
    except ZeroDivisionError:
        logging.error("Failed to parse GPS latitude: %s" % tags['GPS GPSLatitude'])
        return None, None
    try:
        if tags.has_key('GPS GPSLongitude'):
            lon = hms_to_deg(tags['GPS GPSLongitude'])
            if lon is not None:
              lon_ref = tags.get('GPS GPSLongitudeRef')
              if lon_ref == 'W':
                  lon = -lon
        else:
            lon = None
    except ZeroDivisionError:
        logging.error("Failed to parse GPS longitude: %s" % tags['GPS GPSLongitude'])
        return None, None
    return lat, lon
# Some cameras include unnecessary control characters in the day string
def filter_day(day):
    return ''.join([c for c in day if c in string.printable])

def exifread_tags_to_gps_datetime(tags):
    if 'GPS GPSDate' not in tags or 'GPS GPSTimeStamp' not in tags:
        return None
    date = tags.get('GPS GPSDate').printable
    time_ = tags.get('GPS GPSTimeStamp')
    if date == '' or time_ == '':
        return None
    if ':' in date:
        year, month, day = date.split(":")
    elif '/' in date:
        year, month, day = date.split("/")
    else:
        logging.error("Unrecognized date delimiter in: %s" % date)
        return None
    try:
        year = int(year)
        month = int(month)
        day = int(filter_day(day))
        try:
            hour = int(ratio_to_decimal(time_.values[0]))
            minute = int(ratio_to_decimal(time_.values[1]))
            second = int(ratio_to_decimal(time_.values[2]))
        except ZeroDivisionError:
            logging.error("Invalid time ratios: %s" % str(time_.values))
            return None
    except ValueError:
        logging.error("Non-integer date or time: %s, %s" % (str((year,month,day)), str(time_.values)))
        return None
    image_datetime = datetime.datetime(year, month, day, hour, minute, second)
    return image_datetime

def exifread_tags_to_camera_datetime(tags):
    dt = tags.get('Image DateTime', None)
    if dt is None:
        logging.error("Photo does not contain a datetime.")
        return None
    # Trailing time zone info is discarded intentionally, as it's
    # recomputed from the user's lat/lon later.  Warning: storing a
    # naive datetime to Datastore, then retrieving it, will convert
    # the timezone to UTC without adjusting the clock(!)
    
    try:
        camera_datetime = datetime.datetime.strptime(str(dt), "%Y:%m:%d %H:%M:%S")
    except ValueError:
        logging.error("Unparseable camera_datetime: %s" % dt)
        return None
    return camera_datetime
def hms_to_deg(hms):
    h, m, s = [ratio_to_decimal(item) for item in hms.values]
    deg = h + m/60. + s / 3600.
    return deg
