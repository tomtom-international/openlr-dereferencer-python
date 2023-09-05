"Some geo coordinates related tools"
from math import radians, degrees, sin, cos, pi
from typing import Sequence, Tuple, Optional
from geographiclib.geodesic import Geodesic
from openlr import Coordinates
from shapely.geometry import LineString
from itertools import tee
import numpy as np


def distance(point_a: Coordinates, point_b: Coordinates) -> float:
    "Returns the distance of two coordinates from an equal area projection, assuming units are in meters"
    dist = np.sqrt((point_b.lat - point_a.lat) ** 2 + (point_b.lon - point_a.lon) ** 2)
    return dist


def pairwise(iterable):
    "s -> (s0,s1), (s1,s2), (s2, s3), ..."
    first, second = tee(iterable)
    next(second, None)
    return zip(first, second)


def line_string_length(line_string: LineString) -> float:
    """Returns the length of a line string in meters"""

    length = 0

    for coord_a, coord_b in pairwise(line_string.coords):
        l = np.sqrt((coord_b[0] - coord_a[0]) ** 2 + (coord_b[1] - coord_a[1]) ** 2)
        length += l

    return length


def bearing(point_a: Coordinates, point_b: Coordinates) -> float:
    """Returns the angle between self and other relative to true north
    The result of this function is between -pi, pi, including them"""

    bear = np.arctan2(point_b.lon - point_a.lon, point_b.lat - point_a.lon)
    return bear


def extrapolate(point: Coordinates, dist: float, angle: float) -> Coordinates:
    """Creates a new point that is `dist` meters away in direction `angle`
    NOTE: angle must be in radians bc it should be the output of bearing()
    """
    x0, y0 = point.lon, point.lat
    theta_rad = pi / 2 - angle
    x1 = x0 + dist * cos(theta_rad)
    y1 = y0 + dist * sin(theta_rad)
    return Coordinates(x1, y1)


def interpolate(path: Sequence[Coordinates], distance_meters: float) -> Coordinates:
    """Go `distance` meters along the `path` and return the resulting point
    When the length of the path is too short, returns its last coordinate"""
    remaining_distance = distance_meters
    segments = [(path[i], path[i + 1]) for i in range(len(path) - 1)]
    for point1, point2 in segments:
        segment_length = distance(point1, point2)
        if remaining_distance == 0.0:
            return point1
        if remaining_distance < segment_length:
            angle = bearing(point1, point2)
            return extrapolate(point1, remaining_distance, angle)
        remaining_distance -= segment_length
    return segments[-1][1]


def split_line(line: LineString, meters_into: float) -> Tuple[Optional[LineString], Optional[LineString]]:
    "Splits a line at `meters_into` meters and returns the two parts. A part is None if it would be a Point"
    first_part = []
    second_part = []
    remaining_offset = meters_into
    splitpoint = None
    for point_from, point_to in pairwise(line.coords):
        if splitpoint is None:
            first_part.append(point_from)
            (coord_from, coord_to) = (Coordinates(*point_from), Coordinates(*point_to))
            segment_length = distance(coord_from, coord_to)
            if remaining_offset < segment_length:
                splitpoint = interpolate([coord_from, coord_to], remaining_offset)
                if splitpoint != coord_from:
                    first_part.append(splitpoint)
                second_part = [splitpoint, point_to]
            remaining_offset -= segment_length
        else:
            second_part.append(point_to)
    if splitpoint is None:
        return (line, None)
    first_part = LineString(first_part) if len(first_part) > 1 else None
    second_part = LineString(second_part) if len(second_part) > 1 else None
    return (first_part, second_part)


def join_lines(lines: Sequence[LineString]) -> LineString:
    coords = []
    last = None

    for l in lines:
        cs = l.coords
        first = cs[0]

        if last is None:
            coords.append(first)
        else:
            if first != last:
                raise ValueError("Lines are not connected")

        coords.extend(cs[1:])
        last = cs[-1]

    return LineString(coords)
