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

import shutil
import glob
import os
import argparse

def get_arguments():
    parser = argparse.ArgumentParser(description='Render movie.')
    parser.add_argument('--output_directory', type=str, default='movie')
    parser.add_argument('--renumber_directory', type=str, default='renumber')
    return parser.parse_args()


def main():
    args = get_arguments()
    gs = glob.glob(args.output_directory + "/*")
    gs.sort()
    r = []
    for g in gs:
        r.append(g)

    for i in range(len(r)):
        source = r[i]
        dest = os.path.join(args.renumber_directory, "%05d.png" % i)
        shutil.copyfile(source, dest)


if __name__ == '__main__':
    main()
