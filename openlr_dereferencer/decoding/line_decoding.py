"Contains the decoding logic for line location"

from typing import List, Optional
from openlr import LineLocationReference, LocationReferencePoint
from ..maps import MapReader
from ..observer import DecoderObserver
from .candidates import nominate_candidates, match_tail
from .line_location import build_line_location, LineLocation
from .routes import Route
from .configuration import Config

def dereference_path(
    lrps: List[LocationReferencePoint], reader: MapReader, config: Config, observer: Optional[DecoderObserver]
) -> List[Route]:
    "Decode the location reference path, without considering any offsets"
    first_lrp = lrps[0]
    first_candidates = list(nominate_candidates(first_lrp, reader, config, False))

    if observer is not None:
        observer.on_candidates_found(first_lrp, first_candidates)

    linelocationpath = match_tail(first_lrp, first_candidates, lrps[1:], reader, config, observer)
    return linelocationpath


def decode_line(reference: LineLocationReference, reader: MapReader, config: Config, observer: Optional[DecoderObserver]) -> LineLocation:
    """Decodes an openLR line location reference

    Candidates are searched in a radius of `radius` meters around an LRP."""
    parts = dereference_path(reference.points, reader, config, observer)
    return build_line_location(parts, reference)

