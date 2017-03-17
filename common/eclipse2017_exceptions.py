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

from exceptions import Exception


class Eclipse2017Exception(Exception):
    pass


class CloudStorageError(Eclipse2017Exception):
    pass


class CouldNotObtainCredentialsError(Eclipse2017Exception):
    pass


class FailedToRenameFileError(Eclipse2017Exception):
    pass


class FailedToSaveToDatastoreError(Eclipse2017Exception):
    pass


class FailedToUploadToGCSError(Eclipse2017Exception):
    pass


class UserDeletedError(Eclipse2017Exception):
    pass


class ApplicationIdentityError(Exception):
    pass
class MissingCredentialTokenError(Exception):
    pass
class MissingUserError(Exception):
    pass
