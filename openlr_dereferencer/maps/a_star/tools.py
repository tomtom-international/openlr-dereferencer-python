"Helper functions for A*"

from functools import lru_cache
from typing import Dict, List, Any, TypeVar, AbstractSet
from ..abstract import MapReader, Line, Node
from ..wgs84 import distance


class LRPathNotFoundError(Exception):
    "No path was found through the map"


@lru_cache(maxsize=2)
def heuristic(current: Node, target: Node) -> float:
    """Estimated cost from current to target.

    We use geographical distance here as heuristic here."""
    return distance(current.coordinates, target.coordinates)


def reconstruct_path(reader: MapReader, came_from: Dict[Any, int], current: Node) -> List[Line]:
    "When a path is found, it has to be reconstructed from the way the A* algorithm took."
    cur = current
    total_path = []

    while cur.node_id in came_from.keys():
        line = reader.get_line(came_from[cur.node_id])
        total_path.insert(0, line)
        cur = line.start_node
    return total_path


T = TypeVar("T")


def find_minimum(score: Dict[T, Any], filter_set: AbstractSet[T]) -> T:
    """
    Takes a dictionary, returns the key with the minimal value.

    The values have to be comparable, of course (→ implement __lt__).

    Only values in filter_set will be considered.
    """
    min_id, min_v = None, float("inf")
    for (key, value) in score.items():
        if value < min_v and key in filter_set:
            min_id, min_v = key, value
    return min_id


def tautology(_) -> bool:
    "Returns always True, used as default line filter function."
    return True
