"Some tooling functions for path and offset handling"

from typing import List
from logging import debug
from shapely.geometry import LineString, Point
from shapely.ops import  substring
from openlr import Coordinates, LocationReferencePoint
from ..maps import Line
from ..maps.wgs84 import project_along_path
from .routes import Route, PointOnLine


def add_offsets(path: List[Line], p_off: float, n_off: float) -> List[Coordinates]:
    "Add the absolute meter offsets to `path` and return the resulting coordinate list"
    if len(path) == 1:
        # Special case where the path has only one line
        # Trim the single line by the start and end offset
        line = path[0]
        geometry = line.geometry
        length = line.length

        start_fraction = p_off / length
        stop_fraction = 1.0 - (n_off / length)
        trimmed_geometry = substring(geometry, start_fraction, stop_fraction, normalized=True)

        return [Coordinates(*c) for c in trimmed_geometry.coords]
    else:
        # Path has multiple lines

        # Trim the first line by the start offset
        first_line = path[0]
        first_line_geometry = first_line.geometry
        first_line_length = first_line.length

        start_fraction = p_off / first_line_length
        first_line_trimmed_geometry = substring(first_line_geometry, start_fraction, 1.0, normalized=True)

        # Trim the last line by the end offset
        last_line = path[-1]
        last_line_geometry = last_line.geometry
        last_line_length = last_line.length

        stop_fraction = 1.0 - (n_off / last_line_length)
        last_line_trimmed_geometry = substring(last_line_geometry, 0.0, stop_fraction, normalized=True)

        # Gather all coordinates
        all_coordinates = []

        for c in first_line_trimmed_geometry.coords:
            all_coordinates.append(Coordinates(*c))

        for intermediate_line in path[1:-1]:
            for c in intermediate_line.geometry.coords:
                all_coordinates.append(Coordinates(*c))

        for c in last_line_trimmed_geometry.coords:
            all_coordinates.append(Coordinates(*c))

        # Remove duplicate consecutive coordinates
        coordinates_without_duplicates = []
        previous = None

        for c in all_coordinates:
            if previous != None and c == previous:
                continue
            coordinates_without_duplicates.append(c)
            previous = c

        return coordinates_without_duplicates


def remove_offsets(path: Route, p_off: float, n_off: float) -> Route:
    """Remove start+end offsets, measured in meters, from a route and return the result"""
    debug(f"Will consider positive offset = {p_off} m and negative offset {n_off} m.")
    lines = path.lines
    debug(f"This routes consists of {lines} and is {path.length()} m long.")
    # Remove positive offset
    debug(f"fist line's offset is {path.absolute_start_offset}")
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
        PointOnLine(start_line, remaining_poff / start_line.length),
        lines,
        PointOnLine(end_line, 1.0 - remaining_noff / end_line.length)
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
