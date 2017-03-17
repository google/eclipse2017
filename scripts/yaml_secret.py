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

"""Convert a TLS certificate and key to YAML form as required by GKE.
Optionally, will create a self-signed certificate suitable for
development work."""


import argparse
import base64
import os
import subprocess
import sys

DEFAULT_CERTFILE="/tmp/snakeoil.crt"
DEFAULT_KEYFILE="/tmp/snakeoil.key"
DEFAULT_YAML_OUTPUT="/tmp/snakeoil.yaml"


SECRET_FILE_TEMPLATE = \
"""apiVersion: v1
kind: Secret
type: Opaque
metadata:
    name: eclipse2017
data:
    tls.crt: {0}
    tls.key: {1}"""


def get_arguments():
    parser = argparse.ArgumentParser(description='Encode TLS cert and key in YAML form for GKE.')
    parser.add_argument('--certfile', type=str, default=DEFAULT_CERTFILE,
                        help = 'File to load certificate from')
    parser.add_argument('--keyfile', type=str, default=DEFAULT_KEYFILE, help='File to load secret key from')
    parser.add_argument('--create', default=False, action='store_true')
    parser.add_argument('--save_files', default=False, action='store_true', help='Whether to keep the created self-signed cert and key.')
    parser.add_argument('--yaml_output', type=str, default=DEFAULT_YAML_OUTPUT, help='File to save YAML encoded data to.')
    return parser.parse_args()


def create_secret(certfile, keyfile, secretfile, save_files):
    call = ['openssl', 'req', '-x509', '-nodes', '-days', '365',
            '-newkey', 'rsa:2048', '-out', certfile, '-keyout', keyfile,
            '-subj', '/CN=eclipse2017/O=eclipse2017']
    ret = subprocess.call(call)

    if ret != 0:
        raise RuntimeError('call to openssl failed')

    yaml_secret(certfile, keyfile, secretfile)

    if not save_files:
        os.remove(keyfile)
        os.remove(certfile)


def yaml_secret(certfile, keyfile, secretfile):
    cert = base64.b64encode(open(certfile).read())
    key = base64.b64encode(open(keyfile).read())

    secret = SECRET_FILE_TEMPLATE.format(cert, key)

    with open(secretfile, 'w') as f:
        f.write(secret)


def main():
    args  = get_arguments()
    if args.create:
      create_secret(args.certfile, args.keyfile, args.yaml_output, args.save_files)
    else:
      yaml_secret(args.certfile, args.keyfile, args.yaml_output)


if __name__ == '__main__':
    main()
