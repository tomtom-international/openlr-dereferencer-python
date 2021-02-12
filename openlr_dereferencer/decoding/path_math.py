"Functions for reckoning with paths, bearing, and offsets"

from math import degrees
from typing import List
from logging import debug
from shapely.geometry import LineString, Point
from shapely.ops import substring
from openlr import Coordinates, LocationReferencePoint
from .error import LRDecodeError
from .routes import Route, PointOnLine
from ..maps import Line
from ..maps.wgs84 import interpolate, bearing, line_string_length


def remove_offsets(path: Route, p_off: float, n_off: float) -> Route:
    """Remove start+end offsets, measured in meters, from a route and return the result"""
    debug(f"Will consider positive offset = {p_off} m and negative offset {n_off} m.")
    lines = path.lines
    debug(f"This routes consists of {lines} and is {path.length()} m long.")
    # Remove positive offset
    debug(f"first line's offset is {path.absolute_start_offset}")
    remaining_poff = p_off + path.absolute_start_offset
    while remaining_poff >= lines[0].length:
        debug(f"Remaining positive offset {remaining_poff} is greater than "
              f"the first line. Removing it.")
        remaining_poff -= lines.pop(0).length
        if not lines:
            raise LRDecodeError("Offset is bigger than line location path")
    # Remove negative offset
    remaining_noff = n_off + path.absolute_end_offset
    while remaining_noff >= lines[-1].length:
        debug(f"Remaining negative offset {remaining_noff} is greater than "
              f"the last line. Removing it.")
        remaining_noff -= lines.pop().length
        if not lines:
            raise LRDecodeError("Offset is bigger than line location path")
    start_line = lines.pop(0)
    if lines:
        end_line = lines.pop()
    else:
        end_line = start_line
    return Route(
        PointOnLine.from_abs_offset(start_line, remaining_poff),
        lines,
        PointOnLine.from_abs_offset(end_line, end_line.length - remaining_noff)
    )


def coords(lrp: LocationReferencePoint) -> Coordinates:
    "Return the coordinates of an LRP"
    return Coordinates(lrp.lon, lrp.lat)


def project(line: Line, coord: Coordinates) -> PointOnLine:
    """Computes the nearest point to `coord` on the line

    Returns: The point on `line` where this nearest point resides"""
    fraction = line.geometry.project(Point(coord.lon, coord.lat), normalized=True)

    to_projection_point = substring(line.geometry, 0.0, fraction, normalized=True)
    meters_to_projection_point = line_string_length(to_projection_point)
    length_fraction = meters_to_projection_point / line.length
    return PointOnLine(line, length_fraction)


def linestring_coords(line: LineString) -> List[Coordinates]:
    "Returns the edges of the line geometry as Coordinate list"
    return [Coordinates(*point) for point in line.coords]


def compute_bearing(
        lrp: LocationReferencePoint,
        candidate: PointOnLine,
        is_last_lrp: bool,
        bear_dist: float
) -> float:
    "Returns the bearing angle of a partial line in degrees in the range 0.0 .. 360.0"
    line1, line2 = candidate.split()
    if is_last_lrp:
        if line1 is None:
            return 0.0
        coordinates = linestring_coords(line1)
        coordinates.reverse()
        relative_offset = 1.0 - candidate.relative_offset
    else:
        if line2 is None:
            return 0.0
        coordinates = linestring_coords(line2)
        relative_offset = candidate.relative_offset
    absolute_offset = candidate.line.length * relative_offset
    bearing_point = interpolate(coordinates, bear_dist)
    bear = bearing(coordinates[0], bearing_point)
    return degrees(bear) % 360
