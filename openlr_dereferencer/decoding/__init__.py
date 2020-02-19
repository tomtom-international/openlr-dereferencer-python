"""The module doing the actual decoding work.
This includes finding candidates, rating them and choosing the best path"""

from typing import TypeVar
from openlr import LineLocation as LineLocationRef, PointAlongLineLocation, Coordinates
from ..maps import MapReader, Line
from .tools import LRDecodeError
from .line_decoding import decode_line
from .line_location import LineLocation
from .point_locations import decode_pointalongline, PointAlongLine

SEARCH_RADIUS = 100.0

LR = TypeVar("LocationReference", LineLocationRef, PointAlongLineLocation)
MAP_OBJECTS = TypeVar("MapObjects", LineLocation, Coordinates, PointAlongLine)


def decode(reference: LR, reader: MapReader, radius: float = SEARCH_RADIUS) -> MAP_OBJECTS:
    """Translates an openLocationReference into a real location on your map.

    Args:
        reference: The location reference you want to decode
        reader: A reader class for the map on which you want to decode
        radius: The search path for the location's components' candidates

    Returns:
        This function will return one or more map object, optionally wrapped into some class.
        Here is an overview for what reference type will result in which return type:

        reference                     | returns
        ------------------------------|-------------------------------
        openlr.GeoCoordinateLocation  | Node
        openlr.LineLocation           | openlr_dereferencer.LineLocation
        openlr.PointAlongLine         | PointAlongLineLocation
    """
    if isinstance(reference, LineLocationRef):
        return decode_line(reference, reader, radius)
    elif isinstance(reference, PointAlongLineLocation):
        return decode_pointalongline(reference, reader, radius)
    else:
        raise LRDecodeError("Currently, the following reference types are supported:"
                            " · openlr.LineLocation"
                            " · openlr.PointAlongLineLocation."
                            f"'{reference}' is none of them.")
