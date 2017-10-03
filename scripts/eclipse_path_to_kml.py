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

"""Convert NASA public domain eclipse path data to KML"""


import argparse
import urllib2
import urllib
from eclipse_gis import eclipse_gis
from BeautifulSoup import BeautifulSoup

# Download this URI with curl (urllib2.urlopen does not work):
# https://eclipse.gsfc.nasa.gov/SEpath/SEpath2001/SE2017Aug21Tpath.html
DEFAULT_URI='file:///tmp/SE2017Aug21Tpath.html'

DEFAULT_KML_OUTPUT='/tmp/path.kml'
DEFAULT_TSV_OUTPUT='/tmp/path.tsv'

KML_HEADER = """<?xml version='1.0' encoding='UTF-8'?>
<kml xmlns='http://www.opengis.net/kml/2.2'>
<Document>
<!-- All eclipse calculations are by Fred Espenak, and he assumes full responsibility for their accuracy. Permission is freely granted to reproduce this data when accompanied by an acknowledgment: "Eclipse Predictions by Fred Espenak, NASA's GSFC" -->
<name>Untitled layer</name>
"""
KML_FOOTER = """</Document></kml>"""

KML_POLYGON = """
<Placemark>
<name>Polygon 3</name>
<Polygon>
<outerBoundaryIs>
<LinearRing>
<tessellate>1</tessellate>
<coordinates>%s</coordinates>
</LinearRing>
</outerBoundaryIs>
</Polygon>
</Placemark>"""

KML_POINT = """
<Placemark>
<name>Point %d</name>
<Point>
<coordinates>%5.2f,%5.2f,0.0</coordinates>
</Point>
</Placemark>"""

def get_arguments():
    parser = argparse.ArgumentParser(description='Download NASA public domain eclipse path data.')
    parser.add_argument('--uri', type=str, default=DEFAULT_URI,
                        help = 'URI to load data from')
    parser.add_argument('--kml_output_file', type=str, default=DEFAULT_KML_OUTPUT,
                        help = 'KML Output file to write')
    parser.add_argument('--tsv_output_file', type=str, default=DEFAULT_TSV_OUTPUT,
                        help = 'TSV Output file to write')
    parser.add_argument('--write_points', type=bool, default=False,
                        help = 'Whether to write individual points')
    parser.add_argument('--write_polygon', type=bool, default=True,
                        help = 'Whether to write enclosing polygon')
    return parser.parse_args()


def main():
    args = get_arguments()
    # Not sure why urllib2 doesn't support the NASA url.  It returns 403.
    # Try adding more to the accept header
    req = urllib2.Request(args.uri, headers={'User-Agent' : "curl/7.35.0",
                                             'Accept': 'text/html'})
    try:
      response = urllib2.urlopen(req)
    except urllib2.HTTPError, e:
      print e.fp.read()
    else:
      html = response.read()
      doc = BeautifulSoup(html, convertEntities=BeautifulSoup.HTML_ENTITIES)
      data =  doc.body.find('pre').text.replace("\r", "\n").split("\n")
      times, points = eclipse_gis.load_data(data)
      kml_f = open(args.kml_output_file, "w")
      tsv_f = open(args.tsv_output_file, "w")
      kml_f.write(KML_HEADER)
      # Note: all lat/long pairs have to be swapped during input to output format conversion
      if args.write_points:
        # Northern Limit
        for i, point in enumerate(points):
          kml_f.write(KML_POINT % (i+1, point[0][1], point[0][0]))
        # Southern Limit
        for i, point in enumerate(points):
          kml_f.write(KML_POINT % (i+1, point[1][1], point[1][0]))
        # Center line
        for i, point in enumerate(points):
          kml_f.write(KML_POINT % (i+1, point[2][1], point[2][0]))

      if args.write_polygon:
        p0 = []
        p1 = []
        for pointgroup in points:
          # Northern limit
          p0.append(pointgroup[0])
          # Southern limit
          p1.append(pointgroup[2])
        r = []
        # Traverse boundary
        # Along Northern limit
        for point in p0:
          r.append((point[1], point[0]))
        # Backwards along Southern limit
        for point in reversed(p1):
          r.append((point[1], point[0]))
        # Write KML format polygon
        s = " ".join(["%5.2f,%5.2f" % p for p in r])
        kml_f.write(KML_POLYGON % s)

        # Write TSV format polygon
        s = "\n".join(["%5.2f\t%5.2f" % p for p in r])
        tsv_f.write(s)

      kml_f.write(KML_FOOTER)
      kml_f.close()
      tsv_f.close()

if __name__ == '__main__':
    # no-op change
    main()
