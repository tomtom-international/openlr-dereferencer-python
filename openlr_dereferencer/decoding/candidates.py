"Contains functions for candidate searching and map matching"

from itertools import product
from typing import Sequence, Tuple, Optional, Iterable, List, NamedTuple
from logging import debug
from openlr import FRC, LocationReferencePoint
from ..maps import shortest_path, MapReader, Line, path_length
from ..maps.a_star import LRPathNotFoundError
from ..maps.wgs84 import project_along_path, Coordinates
from .scoring import score_lrp_candidate
from .tools import LRDecodeError, coords, project, PointOnLine

#: Tolerable relative DNP deviation of a path
#:
#: A path may deviate from the DNP by this relative value plus TOLERATED_DNP_DEV in order to be
#: considered. The value here is relative to the expected distance to next point.
MAX_DNP_DEVIATION = 0.3

#: Additional buffer to the range of allowed path distance
#:
#: In order to be considered, a path must not deviate from the DNP value by more than
#: MAX_DNP_DEVIATION (relative value) plus TOLERATED_DNP_DEV. This value is in meters.
TOLERATED_DNP_DEV = 30

#: A filter for candidates with insufficient score. Candidates below this score are not considered
MIN_SCORE = 0.3

#: Partial candidate line threshold, measured in meters
#:
#: To find candidates, the LRP coordinates are projected against any line in the local area.
#: If the distance from the starting point is greater than this threshold, the partial line
#: beginning at the projection point is considered to be the candidate.
CANDIDATE_THRESHOLD = 20

class Candidate(PointOnLine):
    "An LRP candidate, represented by a point on the road network along with its score"
    score: Optional[float] = None
    "The candidate may be bundled together with it's precomputed score."

def generate_candidates(
    lrp: LocationReferencePoint, reader: MapReader, radius: float, is_last_lrp: bool
) -> Iterable[Candidate]:
    "Returns a list of candidate lines for the LRP along with their score."
    debug(f"Finding candidates for LRP {lrp} at {coords(lrp)} in radius {radius}")
    for line in reader.find_lines_close_to(coords(lrp), radius):
        dist = line.length
        reloff = project(line.geometry, coords(lrp))
        # Snap to the relevant end of the line
        if not is_last_lrp and reloff * dist <= CANDIDATE_THRESHOLD:
            reloff = 0.0
        if is_last_lrp and (1 - reloff) * dist <= CANDIDATE_THRESHOLD:
            reloff = 1.0
        # Drop candidate if there is no partial line left
        if is_last_lrp and reloff == 0.0 or not is_last_lrp and reloff == 1.0:
            continue
        candidate = Candidate(line, reloff)
        candidate.score = score_lrp_candidate(lrp, candidate, radius, is_last_lrp)
        if candidate.score >= MIN_SCORE:
            yield candidate


class Route(NamedTuple):
    "A part of a line location path. May contain partial lines."
    start: PointOnLine
    "The point with which this location is starting"
    path_inbetween: List[Line]
    "While the first and the last line may be partial, these are the intermediate lines."
    end: PointOnLine
    "The point on which this location is ending"

    def length(self) -> float:
        "Length of this line location part in meters"
        return path_length(self.path_inbetween) \
            + (1 - self.start.relative_offset) * self.start.line.length \
            + self.end.relative_offset * self.end.line.length


def get_candidate_route(
    map_reader: MapReader, c1: Candidate, c2: Candidate, lfrc: FRC, last_lrp: bool, maxlen: float
) -> Optional[Route]:
    """Returns the shortest path between two LRP candidates, excluding partial lines.

    If it is longer than `maxlen`, it is treated as if no path exists.

    Args:
        map_reader:
            A reader for the map on which the path is searched
        line1:
            The start line.
        line2:
            The end line.
        lfrc:
            "lowest frc".
            Line objects from map_reader with an FRC lower than lfrc will be ignored.
        maxlen: Pathfinding will be canceled after exceeding a length of maxlen.

    Returns:
        If a matching shortest path is found, it is returned as a list of Line objects.
        The returned path excludes the lines the candidate points are on.
        If there is no matching path found, None is returned.
    """
    debug(f"Try to find path between lines {c1.line.line_id, c2.line.line_id}")
    debug(f"Finding path between nodes {c1.line.end_node.node_id, c2.line.start_node.node_id}")
    linefilter = lambda line: line.frc <= lfrc
    try:
        path = shortest_path(c1.line.end_node, c2.line.start_node, linefilter, maxlen=maxlen)
        debug(f"Returning {path}")
        return Route(c1, path, c2)
    except LRPathNotFoundError:
        debug(f"No path found between these nodes")
        return None


def match_tail(
    current: LocationReferencePoint,
    candidates: List[Candidate],
    tail: List[LocationReferencePoint],
    reader: MapReader,
    radius: float,
) -> List[Route]:
    """Searches for the rest of the line location.

    Every element of `candidates` is routed to every candidate for `tail[0]` (best scores first).
    Actually not _every_ element, just as many as it needs until some path matches the DNP.

    If any pair matches, the function calls itself for the rest of `tail` and returns.

    If not, a `LRDecodeError` exception is raised."""
    last_lrp = len(tail) == 1
    # The accepted distance to next point. This helps to save computations and filter bad paths
    minlen = (1 - MAX_DNP_DEVIATION) * current.dnp - TOLERATED_DNP_DEV
    maxlen = (1 + MAX_DNP_DEVIATION) * current.dnp + TOLERATED_DNP_DEV
    # Generate all pairs of candidates for the first two lrps
    next_lrp = tail[0]
    next_candidates = list(generate_candidates(next_lrp, reader, radius, last_lrp))
    pairs = list(product(candidates, next_candidates))
    # Sort by line score pair
    pairs.sort(key=lambda pair: (pair[0][1], pair[1][1]), reverse=True)
    # For every pair of candidates, search for a path matching our requirements
    for (c1, c2) in pairs:
        route = get_candidate_route(reader, c1, c2, current.lfrcnp, last_lrp, maxlen)
        if not route:
            debug("No path for candidate found")
            continue
        length = route.length()
        debug(f"DNP should be {current.dnp} m, is {length} m.")
        # If the path does not match DNP, continue with the next candidate pair
        if length < minlen or length > maxlen:
            debug("Shortest path deviation from DNP is too large, trying next candidate")
            continue
        if last_lrp:
            return [route]
        # If not last LRP, match also the rest of tail
        next_candidates = [
            Candidate(c2.line, c2.relative_offset,
                score_lrp_candidate(next_lrp, c2.line, radius, last_lrp)
            ) for line in route.end[-1].end_node.outgoing_lines()
        ]
        return [route] + match_tail(next_lrp, next_candidates, tail[1:], reader, radius)
    raise LRDecodeError("Decoding was unsuccessful: No candidates left or available.")
