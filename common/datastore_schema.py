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

DATASTORE_USER = 'User'
DATASTORE_PHOTO = 'Photo'
DATASTORE_MOVIE = 'Movie'
DATASTORE_ORIENTED_IMAGE = 'ProcessedImage'

# Movie daemon properties
TOTALITY_IMAGE_TYPE = "totality"
TOTALITY_ORDERING_PROPERTY = "adj_timestamp"

ALLOWED_ENTITIES = {
    DATASTORE_USER: {
        'deleted': {'restricted': True},
        'deleted_date': {'restricted': True},
        'geolat': {'restricted': False},
        'geolng': {'restricted': False},
    },
    DATASTORE_PHOTO: {
        'gcs_upload_failed': {'restricted': False},
        'in_gcs': {'restricted': False},
        'processed': {'restricted': False},
        'uploaded_date': {'restricted': False},
        'user': {'restricted': True},
    },
    DATASTORE_ORIENTED_IMAGE: {
        'upload_date': {'restricted': False},
        'original_photo': {'restricted': True},
        'img_type': {'restricted': False},
        TOTALITY_ORDERING_PROPERTY: {'restricted': False},
    },
    DATASTORE_MOVIE: {
        'contributors': {'restricted': False},
    },
}

JSON_MAPPINGS = {
    DATASTORE_USER: (
        ('geolat', 'v', float),
        ('geolng', 'h', float),
    ),
}

def validate_data(data, allow_restricted_fields, kind):
    """
    Check that all the fields in `data` correspond to fields in
    `ALLOWED_ENTITIES[kind]`. `data` is a dictionary/dictionary subclass, `kind`
    is the datastore entity kind. `allow_restricted_fields` is a bool.
    """
    if kind not in ALLOWED_ENTITIES:
        return False
    for key in data:
        if key not in ALLOWED_ENTITIES[kind]:
            return False
        if (ALLOWED_ENTITIES[kind][key]['restricted']
            and not allow_restricted_fields):
            return False
    return True
