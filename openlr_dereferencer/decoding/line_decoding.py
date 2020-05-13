"Contains the decoding logic for line location"

from typing import List, Optional
from openlr import LineLocation as LineLocationRef, LocationReferencePoint
from ..maps import MapReader, Line
from .candidates import generate_candidates, match_tail
from .line_location import build_line_location, LineLocation
from ..observer import DecoderObserver


def dereference_path(
    lrps: List[LocationReferencePoint], reader: MapReader, radius: float, observer: Optional[DecoderObserver]
    ) -> List[Line]:
    "Decode the location reference path, without considering any offsets"
    first_lrp = lrps[0]
    first_lines = list(generate_candidates(first_lrp, reader, radius, False))
    if observer is not None:
        observer.on_candidates_found(first_lrp, first_lines)
    return match_tail(first_lrp, first_lines, lrps[1:], reader, radius, observer)


def decode_line(reference: LineLocationRef, reader: MapReader, radius: float, observer: Optional[DecoderObserver]
    ) -> LineLocation:
    """Decodes an openLR line location reference

    Candidates are searched in a radius of `radius` meters around an LRP."""
    path = dereference_path(reference.points, reader, radius, observer)
    return build_line_location(path, reference)
