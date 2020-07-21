"Some geo coordinates related tools"
from math import radians, degrees
from typing import Sequence, Tuple, Optional
from geographiclib.geodesic import Geodesic
from openlr import Coordinates
from shapely.geometry import LineString
from itertools import tee


def distance(point_a: Coordinates, point_b: Coordinates) -> float:
    "Returns the distance of two WGS84 coordinates on our planet, in meters"
    geod = Geodesic.WGS84
    (lon1, lat1) = point_a.lon, point_a.lat
    (lon2, lat2) = point_b.lon, point_b.lat
    line = geod.Inverse(lat1, lon1, lat2, lon2, Geodesic.DISTANCE)
    # According to https://geographiclib.sourceforge.io/1.50/python/, the distance between
    # point 1 and 2 is stored in the attribute `s12`.
    return line["s12"]


def pairwise(iterable):
    "s -> (s0,s1), (s1,s2), (s2, s3), ..."
    a, b = tee(iterable)
    next(b, None)
    return zip(a, b)


def line_string_length(line_string: LineString) -> float:
    """Returns the length of a line string in meters"""
    geod = Geodesic.WGS84

    length = 0

    for (p, c) in pairwise(line_string.coords):
        l = geod.Inverse(p[1], p[0], c[1], c[0], Geodesic.DISTANCE)
        length += l["s12"]

    return length


def bearing(point_a: Coordinates, point_b: Coordinates) -> float:
    """Returns the angle between self and other relative to true north

    The result of this function is between -pi, pi, including them"""
    geod = Geodesic.WGS84
    line = geod.Inverse(point_a.lat, point_a.lon, point_b.lat, point_b.lon, Geodesic.AZIMUTH)
    # According to https://geographiclib.sourceforge.io/1.50/python/, the azimuth at the
    # first point in degrees is stored as the attribute `azi1`.
    return radians(line["azi1"])


def extrapolate(point: Coordinates, dist: float, angle: float) -> Coordinates:
    "Creates a new point that is `dist` meters away in direction `angle`"
    lon, lat = point.lon, point.lat
    geod = Geodesic.WGS84
    line = geod.Direct(lat, lon, degrees(angle), dist)
    # According to https://geographiclib.sourceforge.io/1.50/python/, the attributes `lon2`
    # and `lat2` store the second point.
    return Coordinates(line["lon2"], line["lat2"])


def interpolate(path: Sequence[Coordinates], distance_meters: float) -> Coordinates:
    """Go `distance` meters along the `path` and return the resulting point

    When the length of the path is too short, returns its last coordinate"""
    remaining_distance = distance_meters
    segments = [(path[i], path[i + 1]) for i in range(len(path) - 1)]
    for (point1, point2) in segments:
        segment_length = distance(point1, point2)
        if remaining_distance == 0.0:
            return point1
        if remaining_distance < segment_length:
            angle = bearing(point1, point2)
            return extrapolate(point1, remaining_distance, angle)
        remaining_distance -= segment_length
    return segments[-1][1]

def split_line(line: LineString, meters_into: float) -> Tuple[Optional[LineString], Optional[LineString]]:
    first_part = []
    second_part = []
    remaining_offset = meters_into
    splitpoint = None
    for (p, c) in pairwise(line.coords):
        if splitpoint is None:
            first_part.append(p)
            (c1, c2) = (Coordinates(*p), Coordinates(*c))
            if remaining_offset < distance(c1, c2):
                splitpoint = interpolate([c1, c2], remaining_offset)
                if splitpoint != c1:
                    first_part.append(splitpoint)
                second_part = [splitpoint, c]
        else:
            second_part.append(c)
    if splitpoint is None:
        return (line, None)
    first_part = LineString(first_part) if len(first_part) > 1 else None
    second_part = LineString(second_part) if len(second_part) > 1 else None
    return (first_part, second_part)
