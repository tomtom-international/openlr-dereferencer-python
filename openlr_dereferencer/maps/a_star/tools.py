"Helper functions for A*"

from functools import lru_cache
from ..abstract import Node
from ..wgs84 import distance as wgs84_dist
from ..equal_area import distance as ee_dist


class LRPathNotFoundError(Exception):
    "No path was found through the map"


@lru_cache(maxsize=2)
def heuristic(current: Node, target: Node, equal_area: bool = False) -> float:
    """Estimated cost from current to target.

    We use geographical distance here as heuristic here."""
    if not equal_area:
        dist = wgs84_dist(current.coordinates, target.coordinates)
    else:
        dist = ee_dist(current.coordinates, target.coordinates)
    return dist


def tautology(_) -> bool:
    "Returns always True, used as default line filter function."
    return True
