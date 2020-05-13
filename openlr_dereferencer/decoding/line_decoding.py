"Contains the decoding logic for line location"

from typing import List
from openlr import LineLocation as LineLocationRef, LocationReferencePoint
from ..maps import MapReader, Line
from .candidates import generate_candidates, match_tail
from .line_location import build_line_location, LineLocation, Route


def dereference_path(
    lrps: List[LocationReferencePoint], reader: MapReader, radius: float
) -> List[Route]:
    "Decode the location reference path, without considering any offsets"
    first_lrp = lrps[0]
    first_candidates = list(generate_candidates(first_lrp, reader, radius, False))
    linelocationpath = match_tail(first_lrp, first_candidates, lrps[1:], reader, radius)
    print("line location path: ", linelocationpath)
    return linelocationpath


def decode_line(reference: LineLocationRef, reader: MapReader, radius: float) -> LineLocation:
    """Decodes an openLR line location reference

    Candidates are searched in a radius of `radius` meters around an LRP."""
    parts = dereference_path(reference.points, reader, radius)
    return build_line_location(parts, reference)
