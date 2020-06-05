from typing import Sequence, NamedTuple, Optional
from openlr import LocationReferencePoint
from ..decoding.candidate import Candidate
from .abstract import DecoderObserver
from ..maps import Line


class AttemptedRoute(NamedTuple):
    """An attempted route between two lrps"""
    from_lrp: LocationReferencePoint
    to_lrp: LocationReferencePoint
    from_line: Line
    to_line: Line
    success: bool
    path: Optional[Sequence[Line]]


class SimpleObserver(DecoderObserver):
    """A simple observer that collects the information and can be queried after the decoding process is finished"""
    def __init__(self):
        self.candidates = {}
        self.attempted_routes = []

    def on_candidates_found(self, lrp: LocationReferencePoint, candidates: Sequence[Candidate]):
        self.candidates[lrp] = candidates

    def on_route_fail(self, from_lrp: LocationReferencePoint, to_lrp: LocationReferencePoint, from_line: Line, to_line: Line):
        self.attempted_routes.append(AttemptedRoute(from_lrp, to_lrp, from_line, to_line, False, None))

    def on_route_success(self, from_lrp: LocationReferencePoint, to_lrp: LocationReferencePoint, from_line: Line,
                         to_line: Line, path: Sequence[Line]):
        self.attempted_routes.append(AttemptedRoute(from_lrp, to_lrp, from_line, to_line, True, path))


