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

ENV DEBIAN_FRONTEND noninteractive
ENV APT_LISTCHANGES_FRONTEND none

RUN apt-get install -y --no-install-recommends nginx sudo && \
    service nginx stop && \
    mkdir -p /var/run/nginx/cache && \
    apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

CMD ["/usr/sbin/nginx", "-c", "/etc/nginx/nginx.conf"]
