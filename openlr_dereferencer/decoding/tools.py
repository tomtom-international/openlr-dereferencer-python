"Some tooling functions for path and offset handling"

from typing import List, Tuple, NamedTuple, Optional
from logging import debug
from shapely.geometry import LineString, Point, GeometryCollection
from shapely.ops import substring, nearest_points
from openlr import Coordinates, LocationReferencePoint
from ..maps import Line
from ..maps.wgs84 import project_along_path


class PointOnLine(NamedTuple):
    "A point on the road network"
    line: Line
    "The line element on which the point resides"
    relative_offset: float
    """Specifies the relative offset of the point.
    Its value is member of the interval [0.0, 1.0].
    A value of 0 references the starting point of the line."""

    def position(self) -> Coordinates:
        "Returns the actual geo position"
        point = self.line.geometry.interpolate(self.relative_offset, normalized=True)
        return Coordinates(point.x, point.y)

    def split(self) -> Tuple[Optional[LineString], Optional[LineString]]:
        "Splits the Line element that this point is along and returns the halfs"
        if self.relative_offset == 0.0:
            return (None, self.line.geometry)
        elif self.relative_offset == 1.0:
            return (self.line.geometry, None)
        line1 = substring(self.line.geometry, 0.0, self.relative_offset, True)
        line2 = substring(self.line.geometry, self.relative_offset, 1.0, True)
        return (line1, line2)


def add_offsets(path: List[Line], p_off: float, n_off: float) -> List[Coordinates]:
    "Add the absolute meter offsets to `path` and return the resulting coordinate list"
    coordinates = [path[0].start_node.coordinates]
    for line in path:
        coordinates.append(line.end_node.coordinates)
    # If offsets available, correct first / last coordinate
    if p_off > 0.0:
        # first LRP to second one
        coordinates[0] = project_along_path(coordinates, p_off)
    if n_off > 0.0:
        # last LRP to second-last LRP
        coordinates[-1] = project_along_path(coordinates[::-1], n_off)
    return coordinates


def remove_unnecessary_lines(
    path: List[Line], p_off: float, n_off: float
) -> Tuple[List[Line], float, float]:
    """Remove start+end lines shorter than the offset and adjust offsets accordingly

    If the offsets are greater than the first/last line, remove that line from the path.

    Reason: The location reference path may be longer than the line location path
    (which this function has to return)"""
    resulting_path = path[:]
    while resulting_path[0].length < p_off:
        p_off -= resulting_path[0].length
        debug(f"removing {resulting_path[0]} because p_off is {p_off}")
        resulting_path.pop(0)
    while resulting_path[-1].length < n_off:
        n_off -= resulting_path[-1].length
        debug(f"removing {resulting_path[-1]} because n_off is {n_off}")
        resulting_path.pop()
    debug(f"path[n-1] ({resulting_path[-1]}) seems to be longer than n_off {n_off}")
    return resulting_path, p_off, n_off


class LRDecodeError(Exception):
    "An error that happens through decoding location references"


def coords(lrp: LocationReferencePoint) -> Coordinates:
    "Return the coordinates of an LRP"
    return Coordinates(lrp.lon, lrp.lat)

def project(line_string: LineString, coord: Coordinates) -> float:
    "The nearest point to `coord` on the line, as relative distance along it"
    return line_string.project(Point(coord.lon, coord.lat), normalized=True)

def linestring_coords(line: LineString) -> List[Coordinates]:
    "Returns the edges of the line geometry as Coordinate list"
    return [Coordinates(*point) for point in line.coords]
