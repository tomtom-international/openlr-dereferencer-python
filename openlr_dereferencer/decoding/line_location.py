"This module contains the LineLocation class and a builder function for it"

from typing import List, Iterable
from openlr import Coordinates, LineLocation as LineLocationRef
from ..maps import Line
from .tools import remove_offsets
from .routes import Route, PointOnLine


def get_lines(line_location_path: Iterable[Route]) -> List[Line]:
    "Convert a line location path to its sequence of line elements"
    result = []
    for part in line_location_path:
        for line in part.lines:
            if result and result[-1].line_id == line.line_id:
                result.pop()
            result.append(line)
    return result


def combine_routes(line_location_path: Iterable[Route]) -> Route:
    path = get_lines(line_location_path)
    start = PointOnLine(path.pop(0), line_location_path[0].start.relative_offset)
    if path:
        end = PointOnLine(path.pop(), line_location_path[-1].end.relative_offset)
    else:
        end = PointOnLine(start.line, line_location_path[-1].end.relative_offset)
    return Route(start, path, end)

def build_line_location(path: List[Route], reference: LineLocationRef) -> Route:
    """Builds a LineLocation object from the location reference path and the offset values.

    The result will be a trimmed list of Line objects, with minimized offset values"""
    p_off = reference.poffs * path[0].length()
    n_off = reference.noffs * path[-1].length()
    route = remove_offsets(
        combine_routes(path),
        p_off + path[0].absolute_start_offset,
        n_off + path[-1].absolute_end_offset
    )
    return route
