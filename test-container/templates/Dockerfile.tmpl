#
# Copyright 2015 Google Inc.
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

ENV DEBIAN_FRONTEND noninteractive
ENV APT_LISTCHANGES_FRONTEND none
ENV CLOUDSDK_CORE_DISABLE_PROMPTS 1

COPY conf/requirements.txt /tmp/requirements.txt
RUN apt-get install -y --no-install-recommends gcc python-dev && \
  pip install -r /tmp/requirements.txt && \
  apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*
RUN mkdir /var/www
RUN chown www-data:www-data /var/www
USER www-data
RUN curl https://sdk.cloud.google.com | bash && ls /var/www && /var/www/google-cloud-sdk/bin/gcloud config set project {{PROJECT_ID}}

USER root
ENV GOOGLE_APPLICATION_CREDENTIALS=/app/common/service_account.json
ADD application.tar /app
RUN chown -R www-data /app

USER www-data
WORKDIR /app
# No default.
