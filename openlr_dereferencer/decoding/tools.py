"Some tooling functions for path and offset handling"

from typing import List, Tuple, NamedTuple, Optional
from logging import debug
from shapely.geometry import LineString, Point, GeometryCollection
from shapely.ops import substring, nearest_points
from openlr import Coordinates, LocationReferencePoint
from ..maps import Line
from ..maps.wgs84 import project_along_path
from .routes import Route, PointOnLine


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


def remove_offsets(
    path: Route, p_off: float, n_off: float
) -> Route:
    """Remove start+end offsets, measured in meters, from a route.

    Reason: The location reference path may be longer than the line location path
    (which this function has to return)"""
    lines = path.lines
    rel_start_off = path.start.relative_offset
    rel_end_off = path.end.relative_offset
    remaining_poff = p_off
    while remaining_poff > 0.0:
        len0 = lines[0].length * (1.0 - rel_start_off)
        if remaining_poff >= len0:
            lines.pop(0)
            remaining_poff -= len0
            rel_start_off = 0.0
        else:
            break
    remaining_noff = n_off
    while remaining_noff < 1.0:
        len0 = lines[-1].length * rel_end_off
        if remaining_noff >= len0:
            lines.pop()
            remaining_noff -= len0
            rel_end_off = 1.0
        else:
            break
    start_line = lines.pop(0)
    if lines:
        end_line = lines.pop()
    else:
        end_line = start_line
    return Route(
        PointOnLine(start_line, remaining_poff / start_line.length),
        lines,
        PointOnLine(end_line, remaining_noff / end_line.length)
    )


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
