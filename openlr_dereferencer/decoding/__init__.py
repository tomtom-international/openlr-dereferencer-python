"""The module doing the actual decoding work.
This includes finding candidates, rating them and choosing the best path"""

from typing import TypeVar, Optional
from openlr import (
    LineLocation as LineLocationRef,
    PointAlongLineLocation,
    Coordinates,
    GeoCoordinateLocation,
    PoiWithAccessPointLocation,
)
from ..observer import DecoderObserver
from ..maps import MapReader
from .tools import LRDecodeError
from .line_decoding import decode_line
from .line_location import LineLocation
from .point_locations import (
    decode_pointalongline,
    PointAlongLine,
    decode_poi_with_accesspoint,
    PoiWithAccessPoint,
)
from .configuration import Config, DEFAULT_CONFIG, load_config, save_config

LR = TypeVar("LocationReference", LineLocationRef, PointAlongLineLocation, GeoCoordinateLocation)
MAP_OBJECTS = TypeVar("MapObjects", LineLocation, Coordinates, PointAlongLine)

def decode(
    reference: LR, 
    reader: MapReader,
    observer: Optional[DecoderObserver] = None,
    config: Config=DEFAULT_CONFIG
) -> MAP_OBJECTS:
    """Translates an openLocationReference into a real location on your map.

    Args:

        reference:
            The location reference you want to decode
        reader:
            A reader class for the map on which you want to decode
        radius:
            The search path for the location's components' candidates
        observer:
            An observer that collects information when events of interest happen at the decoder
        config:
            A definition of the decoding behaviour providing various settings

    Returns:
        This function will return one or more map object, optionally wrapped into some class.
        Here is an overview for what reference type will result in which return type:

        +-----------------------------------+----------------------------------+
        | reference                         | returns                          |
        +===================================+==================================+
        | openlr.GeoCoordinateLocation      | openlr.Coordinates               |
        +-----------------------------------+----------------------------------+
        | openlr.LineLocation               | openlr_dereferencer.LineLocation |
        +-----------------------------------+----------------------------------+
        | openlr.PointAlongLine             | PointAlongLineLocation           |
        +-----------------------------------+----------------------------------+
        | openlr.PoiWithAccessPointLocation | PoiWithAccessPoint               |
        +-----------------------------------+----------------------------------+
    """
    if isinstance(reference, LineLocationRef):
        return decode_line(reference, reader, config, observer)
    elif isinstance(reference, PointAlongLineLocation):
        return decode_pointalongline(reference, reader, config, observer)
    elif isinstance(reference, GeoCoordinateLocation):
        return reference.point
    elif isinstance(reference, PoiWithAccessPointLocation):
        return decode_poi_with_accesspoint(reference, reader, config, observer)
    else:
        raise LRDecodeError(
            "Currently, the following reference types are supported:\n"
            " · GeoCoordinateLocation\n"
            " · LineLocation\n"
            " · PointAlongLineLocation\n"
            " · PoiWithAccessPointLocation\n"
            f'The value "{reference}" is none of them.'
        )
