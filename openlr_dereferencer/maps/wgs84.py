"Some geo coordinates related tools"
from math import radians, degrees
from typing import Sequence
from geographiclib.geodesic import Geodesic
from openlr import Coordinates


def distance(point_a: Coordinates, point_b: Coordinates) -> float:
    "Returns the distance of two WGS84 coordinates on our planet, in meters"
    geod = Geodesic.WGS84
    (lon1, lat1) = point_a.lon, point_a.lat
    (lon2, lat2) = point_b.lon, point_b.lat
    line = geod.Inverse(lat1, lon1, lat2, lon2, Geodesic.DISTANCE)
    # According to https://geographiclib.sourceforge.io/1.50/python/, the distance between
    # point 1 and 2 is stored in the attribute `s12`.
    return line["s12"]


def bearing(point_a: Coordinates, point_b: Coordinates) -> float:
    """Returns the angle between self and other relative to true north

    The result of this function is between -pi, pi, including them"""
    geod = Geodesic.WGS84
    line = geod.Inverse(point_a.lat, point_a.lon, point_b.lat, point_b.lon, Geodesic.AZIMUTH)
    # According to https://geographiclib.sourceforge.io/1.50/python/, the azimuth at the
    # first point in degrees is stored as the attribute `azi1`.
    return radians(line["azi1"])


def project(point: Coordinates, dist: float, angle: float) -> Coordinates:
    "Creates a new point that is `dist` meters away in direction `angle`"
    lon, lat = point.lon, point.lat
    geod = Geodesic.WGS84
    line = geod.Direct(lat, lon, degrees(angle), dist)
    # According to https://geographiclib.sourceforge.io/1.50/python/, the attributes `lon2`
    # and `lat2` store the second point.
    return Coordinates(line["lon2"], line["lat2"])


def project_along_path(path: Sequence[Coordinates], distance_meters: float) -> Coordinates:
    """Go `distance` meters along the `path` and return the resulting point

    When the length of the path is too short, returns its last coordinate"""
    segments = [(path[i], path[i + 1]) for i in range(len(path) - 1)]
    for (point1, point2) in segments:
        segment_length = distance(point1, point2)
        if distance_meters < segment_length:
            angle = bearing(point1, point2)
            return project(point1, distance_meters, angle)
        distance_meters -= segment_length
    return segments[-1][1]
