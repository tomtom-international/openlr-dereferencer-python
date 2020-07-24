"""
Provides the shortest_path(map, start, end) -> List[Line] function, which
finds a shortest path between two nodes.
"""
from typing import List, Optional, Callable, NamedTuple
from heapq import heapify, heappush, heappop
from functools import total_ordering
from ..abstract import Node, Line
from .tools import heuristic, LRPathNotFoundError, tautology


class Score(NamedTuple):
    """The score of a single item in the search priority queue"""
    f: float
    g: float

@total_ordering
class PQItem(NamedTuple):
    """A single item in the search priority queue"""
    score: Score
    node: Node
    line: Line
    previous: "PQItem"

    def __lt__(self, other):
        return self.score < other.score


def shortest_path(
        start: Node,
        end: Node,
        linefilter: Callable[[Line], bool] = tautology,
        maxlen: float = float("inf"),
) -> List[Line]:
    """
    Returns a shortest path on the map between two nodes, as list of lines.

    Uses the `A*`_ algorithm for this.

    You may filter considered lines with `linefilter` and paths with `maxlen`.

    .. _A*: https://en.wikipedia.org/wiki/A*_search_algorithm

    Args:
        start:
            The node from which the path shall start
        end:
            The destination node of the path
        linefilter:
            The optional function parameter `linefilter(Line) -> bool` allows you to decide
            whether a line is allowed to be part of the path. If the function returns `False`,
            the line will not be taken into account.
            This is used for the 'lowest frc next point' attribute of openLR line references.
        maxlen:
            Maximum allowed path length.
            Abort the search for a shortest-path if this length is exceeded.

    Returns:
        A shortest path between the both nodes, after exclusion of lines according to `linefilter`

        An empty path indicates that start and end node are the same.
    Raises:
        LRPathNotFoundError:
            Raised if no path between the nodes could be found.

            Even if a path exists, this may happen for two reasons:

            * No path exists were all lines pass the `linefilter`
            * All existing paths are longer than `maxlen`
    """

    # The initial queue item
    initial = PQItem(Score(heuristic(start, end), 0), start, None, None)

    # The queue
    open_set = [initial]
    heapify(open_set)

    # The seen items
    closed_set = set()

    # Keep trying while the queue is not empty
    while open_set:
        # Pop the next item from the queue
        current = heappop(open_set)
        current_node = current.node

        # Check if the goal node has been reached
        if current_node.node_id == end.node_id:
            # Build the result path
            lines = []
            c = current

            while c.previous:
                lines.insert(0, c.line)
                c = c.previous

            return lines

        # Check if the item has been seen already
        if current_node.node_id in closed_set:
            continue

        # Add neighbors to the queue
        for line in current_node.outgoing_lines():
            if not linefilter(line):
                continue

            neighbor_node = line.end_node

            if neighbor_node.node_id in closed_set:
                continue

            neighbor_g_score = current.score.g + line.length
            neighbor_f_score = neighbor_g_score + heuristic(neighbor_node, end)

            if neighbor_f_score > maxlen:
                continue

            neighbor = PQItem(
                Score(neighbor_f_score, neighbor_g_score),
                neighbor_node,
                line,
                current
            )

            heappush(open_set, neighbor)

        # Add the current item to the closed set
        closed_set.add(current_node.node_id)

    raise LRPathNotFoundError("No path found")
