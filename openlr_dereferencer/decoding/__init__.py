"""The module doing the actual decoding work.
This includes finding candidates, rating them and choosing the best path"""

from itertools import product
from typing import Sequence, Iterable, Tuple, List, Optional
from logging import debug, basicConfig, DEBUG
from openlr import LineLocation as LineLocationRef, PointAlongLineLocation, Coordinates
from ..maps import shortest_path, MapReader, Line
from ..maps.wgs84 import point_along_line
from .candidates import generate_candidates, match_tail
from .scoring import score_lrp_candidate
from .tools import LRDecodeError
from .line_decoding import decode_line
from .line_location import LineLocation

SEARCH_RADIUS = 100.0

def decode(reference: LineLocationRef, reader: MapReader, radius: float = SEARCH_RADIUS) \
        -> LineLocation:
    """Translates an openLocationReference into a real location on your map.

    Args:
        reference: The location reference you want to decode
        reader: A reader class for the map on which you want to decode
        radius: The search path for the location's components' candidates

    Returns:
        The returned value will be a dereferenced openlr_dereferencer.LineLocation. It contains
        a list of Line objects, which is trimmed by the offset values of the line location.
    """
    return decode_line(reference, reader, radius)
