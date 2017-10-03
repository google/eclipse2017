#
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

import unittest2
import datetime
from google.cloud import datastore
from common import image_sorter
from common import config
import time

class ImageSorterTest(unittest2.TestCase):
    """
    Tests for image_sorter code.
    """

    def test_sort_newest(self):
        datastore_client = datastore.Client(config.PROJECT_ID)
        key = datastore_client.key('Photo', '1')
        entity = datastore.Entity(key=key)
        entity["image_datetime"] = datetime.datetime.utcnow()
        time.sleep(1)
        key = datastore_client.key('Photo', '2')
        entity2 = datastore.Entity(key=key)
        entity2["image_datetime"] = datetime.datetime.utcnow()
        time.sleep(1)
        key = datastore_client.key('Photo', '3')
        entity3 = datastore.Entity(key=key)
        entity3["image_datetime"] = datetime.datetime.utcnow()

        entities = [entity, entity2, entity3]
        self.assertEqual(image_sorter.pick_image(entities), entity3)
        entities = [entity3, entity2, entity]
        self.assertEqual(image_sorter.pick_image(entities), entity3)
        entities = [entity2, entity3, entity]
        self.assertEqual(image_sorter.pick_image(entities), entity3)
