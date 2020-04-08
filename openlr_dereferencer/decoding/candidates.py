"Contains functions for candidate searching and map matching"

from itertools import product
from typing import Sequence, Tuple, Optional, Iterable, List
from logging import debug
from openlr import FRC, LocationReferencePoint
from ..maps import shortest_path, MapReader, Line, path_length
from ..maps.a_star import LRPathNotFoundError
from .scoring import score_lrp_candidate
from .tools import LRDecodeError, coords

# Filters candidate paths with too high DNP deviation from expected value
# The value here is relative to the expected distance to next point
MAX_DNP_DEVIATION = 0.3

# A filter for candidates with insufficient score
MIN_SCORE = 0.3


def generate_candidates(
    lrp: LocationReferencePoint, reader: MapReader, radius: float, is_last_lrp: bool
) -> Iterable[Tuple[Line, float]]:
    """Convenience function for decoding, that returns a list of candidate lines for the LRP along
    with their score."""
    debug(f"Finding candidates for LRP {lrp} at {coords(lrp)} in radius {radius}")
    candidates = list(reader.find_lines_close_to(coords(lrp), radius))
    for candidate in candidates:
        score = score_lrp_candidate(lrp, candidate, radius, is_last_lrp)
        if score >= MIN_SCORE:
            yield (candidate, score)


def get_candidate_route(
    map_reader: MapReader, line1: Line, line2: Line, lfrc: FRC, last_lrp: bool, maxlen: float
) -> Optional[Sequence[Line]]:
    """Returns the shortest path which uses the two given lines as first
    and last step and thus connects both, as well as the length.

    If all paths between the lines are longer than `maxlen`, it is treated as if no path exists.

    Args:
        map_reader: A reader for the map on which the path is searched
        line1: The start line.
        line2: The end line.
        lfrc: "lowest frc".
            Line objects from map_reader with an FRC lower than lfrc will be ignored.
        maxlen: Pathfinding will be canceled after exceeding a length of maxlen.

    Returns:
        If a matching shortest path is found, it is returned as a list of Line objects.
        The returned path includes line1, but not line2.
        If there is no matching path found, None is returned.
    """
    debug(f"Try to find path between lines {line1.line_id, line2.line_id}")
    if line1.line_id == line2.line_id:
        debug("line1 == line2")
        return [line1]
    if last_lrp:
        target_node = line2.end_node
    else:
        target_node = line2.start_node
    linefilter = lambda line: line.frc <= lfrc
    debug(f"Finding path between nodes {line1.end_node.node_id, target_node.node_id}")
    try:
        path = shortest_path(map_reader, line1.end_node, target_node, linefilter, maxlen=maxlen)
        debug(f"Returning {[line1] + path}")
        return [line1] + path
    except LRPathNotFoundError:
        debug(f"No path found between these nodes")
        return None


def match_tail(
    current: LocationReferencePoint,
    candidates: List[Tuple[Line, float]],
    tail: List[LocationReferencePoint],
    reader: MapReader,
    radius: float,
) -> List[Line]:
    """Searches for the rest of the line location.

    Every element of `candidates` is routed to every candidate for `tail[0]` (best scores first).
    Actually not _every_ element, just as many as it needs until some path matches the DNP.

    If any pair matches, the function calls itself for the rest of `tail` and returns.

    If not, a `LRDecodeError` exception is raised."""
    last_lrp = len(tail) == 1
    # The maximum accepted length. This helps A* to save computational time
    maxlen = (1 + MAX_DNP_DEVIATION) * current.dnp
    # Generate all pairs of candidates for the first two lrps
    next_lrp = tail[0]
    next_candidates = list(generate_candidates(next_lrp, reader, radius, last_lrp))
    pairs = list(product(candidates, next_candidates))
    # Sort by line score pair
    pairs.sort(key=lambda pair: (pair[0][1], pair[1][1]), reverse=True)
    # For every pair of candidate lines, search for a matching path
    for ((line1, _), (line2, _)) in pairs:
        path = get_candidate_route(reader, line1, line2, current.lfrcnp, last_lrp, maxlen)
        if not path:
            debug("No path for candidate found")
            continue
        deviation = abs(current.dnp - path_length(path)) / current.dnp
        debug(f"DNP should be {current.dnp} m, is {path_length(path)} m. ({deviation} rel. dev)")
        # If path does not match DNP, continue with the next candidate pair
        if deviation > MAX_DNP_DEVIATION:
            debug("Shortest path deviation is too large, trying next candidate")
            continue
        if last_lrp:
            return path
        # If not last LRP, match also the rest of tail
        next_candidates = []
        for line in path[-1].end_node.outgoing_lines():
            next_candidates.append((line, score_lrp_candidate(next_lrp, line, radius, last_lrp)))
        return path + match_tail(next_lrp, next_candidates, tail[1:], reader, radius)
    raise LRDecodeError()
