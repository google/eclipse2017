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

import math
import pytz
import os
import datetime
import argparse
from google.cloud import datastore
from PIL import Image, ImageDraw, ImageFont

DEFAULT_PROJECT="eclipse-2017-test"

def chunks(list_, num_items):
    """break list_ into n-sized chunks..."""
    results = []
    for i in range(0, len(list_), num_items):
        results.append(list_[i:i+num_items])
    return results

def get_arguments():
    parser = argparse.ArgumentParser(description='Render movie.')
    parser.add_argument('--project_id', type=str, default=DEFAULT_PROJECT)
    parser.add_argument('--photo_table', type=str, default="Photo")
    parser.add_argument('--names', type=str, default="names.txt")
    parser.add_argument('--credits_directory', type=str, default="credits")
    parser.add_argument('--additional_credits', type=str, default="additional_credits.txt")
    parser.add_argument('--rename_credits', type=str, default="rename_credits.txt")
    parser.add_argument('--image_bucket', type=str, default="megamovie")
    return parser.parse_args()

def get_uploaded_volunteers(client, photo_table, image_bucket):
    query = client.query(kind=photo_table)
    query.add_filter('image_bucket', '=', image_bucket)
    query.add_filter('is_adult_content', '=', False)
    query.add_filter('confirmed_by_user', '=', True)
    entities = query.fetch()
    entities = list(query.fetch())
    users = {}
    for entity in entities:
        metadata = {}
        if not entity.has_key('anonymous_photo'):
            continue
        anonymous_photo = entity['anonymous_photo']
        if not entity.has_key('user'):
            continue
        user = entity['user']
        if user not in users:
            users[user] = []
        users[user].append(anonymous_photo)

    o = open("all_users.txt", "wb")
    for user in users:
        o.write(user.name)
        o.write("\n")
    o.close()
    named_users = []
    anon_users = []
    for user in users:
        if not all(users[user]):
            named_users.append(user)
        else:
            anon_users.append(user)

    o = open("named_users.txt", "wb")
    for user in named_users:
        o.write(user.name)
        o.write("\n")
    o.close()
    o = open("anon_users.txt", "wb")
    for user in anon_users:
        o.write(user.name)
        o.write("\n")
    o.close()

    return named_users, anon_users

def get_users(client, users):
    entities = client.get_multi(list(users))
    names = [ entity.get("name", None) for entity in entities ]
    return names

def main():
    args  = get_arguments()
    client = datastore.Client(project=args.project_id)
    named_users, anon_users = get_uploaded_volunteers(client, args.photo_table, args.image_bucket)
    named_user_chunks = chunks(named_users, 500)
    entities = []
    for named_user_chunk in named_user_chunks:
        entities.extend(client.get_multi(named_user_chunk))
    names = [ entity['name'] for entity in entities ]

    additional_credits = [line.strip() for line in open(args.additional_credits).readlines()]
    names.extend(additional_credits)
    s = set(names)
    names = list(s)

    rename_credits = open(args.rename_credits).readlines()
    rename = {}
    for line in rename_credits:
        s = line.split('\t')
        rename[s[0]] = s[1].strip()

    print rename
    new_names = []
    for name in names:
        if name is None: continue
        if name in rename:
            print "Rename user", name, "to", rename[name]
            name = rename[name]
        if '@' in name:
            name = name.split("@")[0]
        name = name.replace("&amp;", "&")
        new_names.append(name)
    names = new_names
    names.sort(key=lambda s: s.lower())

    o = open("names.txt", "wb")
    for name in names:
        o.write(name.encode('utf-8'))
        o.write("\n")
    o.close()

    num_credits_per_frame = 14
    spacing = 10

    count = 0
    index = 0
    frames = []
    frame = []
    for name in names:
        frame.append(name)
        count += 1
        if count == num_credits_per_frame:
            frames.append(frame)
            frame = []
            count = 0
    if len(frame):
        frames.append(frame)

    num_frames = len(frames)
    for i in range(num_frames):
        frame = frames[i]
        im = Image.new("RGBA", (1920, 1080), (0,0,0,255))
        draw = ImageDraw.Draw(im)
        font = ImageFont.truetype("ProductSans-Regular.ttf", 45)

        total_height = 0
        for j in range(len(frame)):
            txt = frame[j]
            width, height = draw.textsize(txt,font=font)
            total_height += (height + spacing)


        # Figure out right x_offset and y_offset from width, height sums above
        y = 1080 / 2 - total_height / 2
        for j in range(len(frame)):
            txt = frame[j]
            width, height = draw.textsize(txt,font=font)
            x = 1920 / 2 - width / 2
            draw.text((x, y), txt, (255,255,255,255), font=font)
            y += (height + spacing)

        new_fname = os.path.join(args.credits_directory, "%05d.png" % i)
        im.save(new_fname)
    # extra frame b/c ffmpeg slideshow shortens last frame

    new_fname = os.path.join(args.credits_directory, "%05d.png" % (i+1))
    im.save(new_fname)

if __name__ == '__main__':
    main()
