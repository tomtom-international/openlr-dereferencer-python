"Contains the decoding logic for line location"

from typing import List, Optional
from openlr import LineLocationReference, LocationReferencePoint
from ..maps import MapReader
from ..observer import DecoderObserver
from .candidate_functions import nominate_candidates, match_tail
from .line_location import build_line_location, LineLocation
from .routes import Route
from .configuration import Config


def dereference_path(
        lrps: List[LocationReferencePoint],
        reader: MapReader,
        config: Config,
        observer: Optional[DecoderObserver]
) -> List[Route]:
    "Decode the location reference path, without considering any offsets"
    forwd_lrp, backwd_lrp = lrps[0], lrps[-1]
    forwd_candidates, backwd_candidates = list(nominate_candidates(forwd_lrp, reader, config, False)), list(nominate_candidates(backwd_lrp, reader, config, False))
    
    
    # print("candidates: ", x=[i for i in first_candidates.score])

    if observer is not None:
        observer.on_candidates_found(first_lrp, first_candidates)

    # linelocationpath = match_tail(first_lrp, first_candidates, lrps[1:], reader, config, observer)
    linelocationpath = match_tail(forwd_lrp, backwd_lrp, forwd_candidates, backwd_candidates, lrps, reader, config, observer)


    return linelocationpath


def decode_line(reference: LineLocationReference, reader: MapReader, config: Config,
                observer: Optional[DecoderObserver]) -> LineLocation:
    """Decodes an openLR line location reference

    Candidates are searched in a radius of `radius` meters around an LRP."""

    # print("Number of lrps: ", len(reference.points), [i for i in reference.points])
    # print("\n lrp_lon lrp_lat lrp_frc lrp_fow lrp_bear lrp_lfrcnp lrp_dnp cand_link_id cand_dir cand_fow cand_frc cand_geo_score cand_fow_score cand_frc_score cand_bear cand_bear_diff cand_score min_score")
    parts = dereference_path(reference.points, reader, config, observer)
    return build_line_location(parts, reference)
