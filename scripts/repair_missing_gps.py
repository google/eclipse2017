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

"""."""

import argparse
from common import repair_missing_gps
from google.cloud import datastore

def get_arguments():
    parser = argparse.ArgumentParser(description='Count the number of photos in an upload session that have GPS')
    parser.add_argument('--project_id', type=str, default="eclipse-2017-test-147301")
    parser.add_argument('--upload_session_id', type=str, default=None)
    return parser.parse_args()

def main():
    args  = get_arguments()

    client = datastore.Client(args.project_id)
    query = client.query(kind="Photo")
    entities = query.fetch()
    upload_session_id = args.upload_session_id
    assert upload_session_id is not None
    filters = []
    filters.append(('upload_session_id', '=', upload_session_id))

    query = client.query(kind="Photo", filters=filters)
    entities = query.fetch()
    results = repair_missing_gps.partition_gps(entities)
    complete_images, incomplete_images = results
    batch = client.batch()
    batch.begin()
    for complete_image in complete_images:
        batch.put(complete_image)

    if len(complete_images) == 1 and len(incomplete_images) > 1:
        print "Repairing incomplete images"
        complete_image = complete_images[0]
        for incomplete_image in incomplete_images:
            repaired_image = repair_missing_gps.update_incomplete(complete_image, incomplete_image)
            print "Repaired", repaired_image.key.name, "from", complete_image.key.name
            batch.put(repaired_image)

    batch.commit()

if __name__ == '__main__':
    main()
