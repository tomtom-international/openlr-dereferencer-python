"Contains the decoding logic for line location"

from typing import List, Optional
from openlr import LineLocationReference, LocationReferencePoint
from ..maps import MapReader
from ..observer import DecoderObserver
from .candidate_functions import nominate_candidates, match_tail
from .line_location import build_line_location, LineLocation
from .routes import Route
from .configuration import Config
from .error import LRFirstLRPNoCandidatesError


def dereference_path(
    lrps: List[LocationReferencePoint],
    reader: MapReader,
    config: Config,
    observer: Optional[DecoderObserver],
    basemap_filter_str: Optional[str] = "",
) -> List[Route]:
    "Decode the location reference path, without considering any offsets"
    first_lrp = lrps[0]
    first_candidates = list(
        nominate_candidates(
            first_lrp, reader, config, observer, False, basemap_filter_str
        )
    )

    # try again without filter if no candidates found
    if len(first_candidates) == 0:
        if basemap_filter_str != "":
            first_candidates = list(
                nominate_candidates(first_lrp, reader, config, observer, False)
            )

    # raise error if no candidates found
    if len(first_candidates) == 0:
        raise LRFirstLRPNoCandidatesError(
            "Decoding was unsuccessful: no candidates found for first lrp."
        )
    linelocationpath = match_tail(
        first_lrp, first_candidates, lrps[1:], reader, config, observer
    )
    return linelocationpath


def decode_line(
    reference: LineLocationReference,
    reader: MapReader,
    config: Config,
    observer: Optional[DecoderObserver],
    basemap_filter_str: Optional[str] = "",
) -> LineLocation:
    """Decodes an openLR line location reference

    Candidates are searched in a radius of `radius` meters around an LRP."""
    parts = dereference_path(
        reference.points, reader, config, observer, basemap_filter_str
    )
    return build_line_location(parts, reference, config.equal_area)
