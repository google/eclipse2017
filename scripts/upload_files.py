"""Make authenticated requests to eclipse backends."""

import functools
import multiprocessing
import argparse
import json
import os
import requests
import math
import time
import hashlib

from common.id_token import get_id_token
from common.secret_keys import IDEUM_APP_SECRET

def get_arguments():
    parser = argparse.ArgumentParser(description='Make authenticated request to eclipse backend')
    parser.add_argument('--images_file', type=str, default="images.txt")
    parser.add_argument('--image_bucket', type=str, default="volunteer_test")
    parser.add_argument('--hostname', type=str, default="localhost")
    parser.add_argument('--pool_size', type=int, default=1)
    return parser.parse_args()


def upload_post(id_token, hostname, image_bucket, session_id, image_file):
    data = open(image_file, 'rb').read()
    filename = 'f.jpg'
    headers =  { 'x-idtoken': id_token, 'x-uploadsessionid': session_id, 'x-image-bucket': image_bucket,
                 'x-cc0-agree': 'true', 'x-public-agree': 'true' }
    url = 'https://%s/services/upload/' % hostname
    files = {'file': (os.path.basename(image_file), data)}
    r = requests.post(url, headers=headers, files=files, verify=False)

    return r

def confirm_post(id_token, hostname, session_id, filenames):
    headers =  { 'x-idtoken': id_token }#, 'x-ideum-app-secret': IDEUM_APP_SECRET}
    data = {'upload_session_id': session_id, 'filenames': map(os.path.basename, filenames)}
    url = 'https://%s/services/photo/confirm' % hostname
    r = requests.post(url, headers=headers, json=data, verify=False)

    return r

def main():
    args  = get_arguments()
    id_token = get_id_token()
    session_id = hashlib.sha256(str(math.floor(time.time() / 1000))).hexdigest()
    images = [filename.strip() for filename in open(args.images_file).readlines()]
    pool = multiprocessing.Pool(args.pool_size)
    upload_fn = functools.partial(upload_post, id_token, args.hostname, args.image_bucket, session_id)
    results = pool.map(upload_fn, images)
    print [(result.status_code, result.text) for result in results]
    r = confirm_post(id_token, args.hostname, session_id, images)
    print r
    print r.content

if __name__ == '__main__':
    main()
