from typing import NamedTuple, Tuple, Optional, List
from shapely.geometry import LineString
from shapely.ops import substring, linemerge
from openlr import Coordinates
from ..maps.abstract import Line, path_length

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

class Route(NamedTuple):
    "A part of a line location path. May contain partial lines."
    start: PointOnLine
    "The point with which this location is starting"
    path_inbetween: List[Line]
    "While the first and the last line may be partial, these are the intermediate lines."
    end: PointOnLine
    "The point on which this location is ending"

    @property
    def lines(self) -> List[Line]:
        "Returns all lines that take part in the route"
        result = [self.start.line]
        for line in self.path_inbetween:
            if line.line_id != result[-1].line_id:
                result.append(line)
        if self.end.line.line_id == result[-1].line_id:
            result.pop()
        result.append(self.end.line)
        return result

    def length(self) -> float:
        "Length of this line location part in meters"
        lines = self.lines
        result = path_length(lines)
        if self.start.relative_offset > 0.0:
            result -= lines[0].length * self.start.relative_offset
        if self.end.relative_offset < 1.0:
            result -= lines[-1].length * (1.0 - self.end.relative_offset)
        return result

    @property
    def absolute_start_offset(self) -> float:
        "Offset on the starting line in meters"
        return self.start.line.length * self.start.relative_offset

    @property
    def absolute_end_offset(self) -> float:
        "Offset on the ending line in meters"
        return self.end.line.length * (1.0 - self.end.relative_offset)

    @property
    def shape(self) -> LineString:
        "Returns the shape of the route. The route is has to be continuous."
        if self.start.line.line_id == self.end.line.line_id:
            return substring(self.start.line.geometry, self.start.relative_offset, self.end.relative_offset, normalized=True)
        return linemerge(
            [self.start.split()[1]] +
            [line.geometry for line in self.path_inbetween] +
            [self.end.split()[0]]
        )

    def coordinates(self) -> List[Coordinates]:
        "Returns all Coordinates of this line location"
        return [Coordinates(lon, lat) for (lon, lat) in self.shape.coords]