"This module contains the LineLocation class and a builder function for it"

from typing import List
from openlr import Coordinates, LineLocation as LineLocationRef
from ..maps import Line
from .tools import add_offsets, remove_unnecessary_lines


class LineLocation:
    """A dereferenced line location. Create it from a list of lines along with the line reference.

    The line location path is saved in the attribute `lines`
    and is a list of `Line` elements coming from the map reader, on which it was decoded.

    The attributes `p_off` and `n_off` contain the absolute offset at the start/end of the
    line location path. They are measured in meters.

    The method `coordinates()` returns the exact coordinates of the line location."""

    lines: List[Line]
    p_off: float
    n_off: float

    def __init__(self, lines: List[Line], p_off: float, n_off: float):
        self.lines = lines
        self.p_off = p_off
        self.n_off = n_off

    def coordinates(self) -> List[Coordinates]:
        "Return the exact list of coordinates defining the line location path"
        return add_offsets(self.lines, self.p_off, self.n_off)


def build_line_location(lines: List[Line], reference: LineLocationRef) -> LineLocation:
    """Builds a LineLocation object from the location reference path and the offset values.

    The result will be a trimmed list of Line objects, with minimized offset values"""
    p_off = reference.poffs * reference.points[0].dnp
    n_off = reference.noffs * reference.points[-2].dnp
    adjusted_lines, p_off, n_off = remove_unnecessary_lines(lines, p_off, n_off)
    return LineLocation(adjusted_lines, p_off, n_off)
