"Decoding logic for point (along line, ...) locations"

from typing import NamedTuple, List, Tuple
from openlr import (
    Coordinates,
    PointAlongLineLocation,
    Orientation,
    SideOfRoad,
    PoiWithAccessPointLocation,
)
from ..maps import MapReader, path_length
from ..maps.abstract import Line
from ..maps.wgs84 import project_along_path
from .line_decoding import dereference_path
from . import LRDecodeError


class PointAlongLine(NamedTuple):
    """A dereferenced point along line location.

    Contains the coordinates as well as the road on which it was located."""

    line: Line
    positive_offset: float
    side: SideOfRoad
    orientation: Orientation

    def coordinates(self) -> Coordinates:
        "Returns the actual geo coordinate"
        return project_along_path(list(self.line.coordinates()), self.positive_offset)


def point_along_linelocation(path: List[Line], length: float) -> Tuple[Line, float]:
    """Steps `length` meters into the `path` and returns the and the Line + offset in meters.

    If the path is exhausted (`length` longer than `path`), raises an LRDecodeError."""
    leftover_length = length
    for road in path:
        if leftover_length > road.length:
            leftover_length -= road.length
        else:
            return road, leftover_length
    raise LRDecodeError("Path length exceeded while projecting point")


def decode_pointalongline(
    reference: PointAlongLineLocation, reader: MapReader, radius: float
) -> PointAlongLine:
    "Decodes a point along line location reference"
    path = dereference_path(reference.points, reader, radius)
    absolute_offset = path_length(path) * reference.poffs
    line_object, line_offset = point_along_linelocation(path, absolute_offset)
    return PointAlongLine(line_object, line_offset, reference.sideOfRoad, reference.orientation)


class PoiWithAccessPoint(NamedTuple):
    "A dereferenced POI with access point location."
    line: Line
    positive_offset: float
    side: SideOfRoad
    orientation: Orientation
    poi: Coordinates

    def access_point_coordinates(self) -> Coordinates:
        "Returns the geo coordinates of the access point"
        return project_along_path(list(self.line.coordinates()), self.positive_offset)


def decode_poi_with_accesspoint(
    reference: PoiWithAccessPointLocation, reader: MapReader, radius: float
) -> PoiWithAccessPoint:
    "Decodes a point along line location reference into a Coordinates tuple"
    path = dereference_path(reference.points, reader, radius)
    absolute_offset = path_length(path) * reference.poffs
    line, line_offset = point_along_linelocation(path, absolute_offset)
    return PoiWithAccessPoint(
        line,
        line_offset,
        reference.sideOfRoad,
        reference.orientation,
        Coordinates(reference.lon, reference.lat),
    )
