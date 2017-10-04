import exifread
from gps import exifread_tags_to_latlon, hms_to_deg, exifread_tags_to_gps_datetime, exifread_tags_to_camera_datetime
def _extract_exif_metadata(fpath):
    """
    Extracts EXIF metadata corresponding to image with fpath
    Returns metadata_dictionary
    """

    metadata = {}
    # convert to exifread support
    f = open(fpath, 'rb')
    try:
        tags = exifread.process_file(f)
    except Exception as e:
        print "exifread failed to process file:", fpath, e
        lat, lon, image_datetime = None, None, None
    else:
        lat, lon = exifread_tags_to_latlon(tags)
        image_datetime = exifread_tags_to_gps_datetime(tags)
        camera_datetime = exifread_tags_to_camera_datetime(tags)
    if image_datetime:
        metadata['image_datetime'] = image_datetime
    if camera_datetime:
        metadata['camera_datetime'] = camera_datetime
    else:
        print "Image", fpath, "is missing camera datetime"
    if lat:
        metadata['lat'] = lat
    if lon:
        metadata['lon'] = lon
    return metadata

def _extract_image_metadata(filename, format_, width, height, bucket):
    """
    Extracts image format-specific metadata corresponding to image with fpath
    Returns metadata_dictionary
    """
    metadata = {}
    metadata['image_type'] = unicode(format_)
    metadata['width'] = width
    metadata['height'] = height
    return metadata
