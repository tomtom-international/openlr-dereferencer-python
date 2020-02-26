"""
Provides the shortest_path(map, start, end) -> List[Line] function, which
finds a shortest path between two nodes.
"""
from typing import AbstractSet, List, Dict, Optional, Callable
from queue import PriorityQueue
from ..abstract import MapReader, Line, Node
from .tools import heuristic, reconstruct_path, find_minimum, LRPathNotFoundError, tautology


def shortest_path(
    reader: MapReader,
    start: Node,
    end: Node,
    linefilter: Callable[[Line], bool] = tautology,
    maxlen: float = float("inf"),
) -> List[Line]:
    """
    Returns a shortest path on the map between two nodes, as list of lines.

    Uses the A* algorithm for this.
    https://en.wikipedia.org/wiki/A*_search_algorithm

    A `LRPathNotFoundError` is raised if there is no path between the nodes.

    An empty path indicates that start and end node are the same.

    The optional function parameter `linefilter(Line) -> bool` decides whether
    a line is allowed to be part of the path. If the function returns `False`, the line
    will not be taken into account.
    This is used for the 'lowest frc next point' attribute of openLR line references.
    """

    def g_score(node: Node) -> float:
        "Returns the cost from the start node to this node, if available, else infinity"
        return g_dict.get(node.node_id, float("inf"))

    open_set = {start.node_id}
    closed_set = set()
    came_from = {}
    g_dict = {start.node_id: 0}
    f_dict = {start.node_id: heuristic(start, end)}

    while open_set:
        # Getting the below minimum would be much cheaper in a heap.
        # Unfortunately, there is no updatable heap in the standard library.
        current_id = find_minimum(f_dict, open_set)
        current = reader.get_node(current_id)
        if current_id == end.node_id:
            return reconstruct_path(reader, came_from, current)

        open_set.remove(current_id)
        closed_set.add(current_id)

        for line in current.outgoing_lines():
            if not linefilter(line):
                continue
            neighbor = line.end_node
            neighbor_id = neighbor.node_id
            if neighbor_id in closed_set:
                continue

            tentative_score = g_score(current) + line.length
            if tentative_score > maxlen:
                continue
            elif tentative_score < g_score(neighbor) + heuristic(neighbor, end):
                # The path to neighbor is better than any known. Save it.
                came_from[neighbor_id] = line.line_id
                g_dict[neighbor_id] = tentative_score
                f_dict[neighbor_id] = tentative_score + heuristic(neighbor, end)
                open_set.add(neighbor_id)

    raise LRPathNotFoundError("No path found")
