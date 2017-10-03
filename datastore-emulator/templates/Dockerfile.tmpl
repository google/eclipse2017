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

FROM {{GCR_PREFIX_WITH_SLASH}}base-container:latest

USER root

ENV CLOUDSDK_CORE_DISABLE_PROMPTS 1
ENV DATA_DIR "/data"

RUN apt-get install -yqq python openjdk-8-jre && \
    curl https://sdk.cloud.google.com | bash && \
    /root/google-cloud-sdk/bin/gcloud config set project {{PROJECT_ID}} && \
    /root/google-cloud-sdk/bin/gcloud components install beta && \
    /root/google-cloud-sdk/bin/gcloud components install cloud-datastore-emulator && \
    apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

EXPOSE {{HOST_PORT}}

CMD /root/google-cloud-sdk/bin/gcloud beta emulators datastore start --no-legacy --host-port=0.0.0.0:{{HOST_PORT}} --consistency="1.0" --data-dir=$DATA_DIR
