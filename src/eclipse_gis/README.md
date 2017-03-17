eclipse_gis is a simple library for computing basic geometric operations on an
Eclipse Path.  It can be used to convert a user's lat/long (GPS location) to a
value 0...1 along the center line of the eclipse's path.  That value can be used
to order images taken by photographers within the eclipse's path of totality.

Path data is derived from this table:
https://eclipse.gsfc.nasa.gov/SEpath/SEpath2001/SE2017Aug21Tpath.html
which may be freely redistributed with this attribution: "Eclipse Predictions by Fred Espenak, NASA's GSFC"

Basic terms:

1) eclipse path boundary: this is the region of an eclipse where viewers will
see a total eclipse (equivalent to the location of the Moon's umbral shadow on
the Earth surface).  The path boundary forms a closed polygon.

2) eclipse center line: this is the region of an eclipse where viewers see a
total eclipse for the maximum time

3) point: a location given in lat/long coordinates

Given an eclipse path boundary in lat/long coordinates, a point:

1) can be tested whether the point is within the eclipse path boundary

2) can be tested to find the closest point on the eclipse center line

3) can be converted to a value 0..1 representing the location of the point on
the eclipse center line.

Important assumptions:

The method is approximate:

1) It assumes a flat earth model but is reasonable for the eclipse path as long
as we aren't comparing two photos which were taken very far (>500mi) apart.  To
make this more accurate we woudl have to move to great circle distances.

2) It pretends that the center line path is completely straight so that we can
use "nearest point" calculations.  In the area where the path is highly curved,
there are some counterintuitive results.  For example, it is possible that two
points may be misordered.  To improve on this, we would have to "sweep" a line
along the length of the totality path and calculate projections along that axis,
rather than finding the shortest point.

# Example usage:
filename = "data/eclipse_data.txt"
boundary, center_line = load_data(filename)
eg = EclipseGIS(boundary, center_line)
eclipse_polygon = load_data(filename)
for point in [
    # Outside path of totality
    Point(45.77, -99.68),
    # Near the center of US
    Point(42.05, -100.75),
    # Corvallis
    Point(44.56, -123.24),
    # Westernmost point of US Eclipse
    Point(44.83, -124),
    # Easternmost point of US Eclipse
    Point(32.9, -79.36),
    ]:
  print eg.test_point_within_eclipse_boundary(point)
  print eg.find_nearest_point_on_line(point)
  print eg.interpolate_nearest_point_on_line(point)
