"""An abstract `MapReader` base class, which must be implemented for each
map format to decode location references on."""
from abc import ABC, abstractmethod
from typing import Iterable, Hashable
from openlr import Coordinates, FOW, FRC

class Line(ABC):
    "Abstract Line class, modelling a line coming from a map reader"

    @property
    @abstractmethod
    def line_id(self) -> Hashable:
        "Returns the id of the line. A type is not specified here."
        pass

    @property
    @abstractmethod
    def start_node(self) -> 'Node':
        "Returns the node from which this line starts"
        pass

    @property
    @abstractmethod
    def end_node(self) -> 'Node':
        "Returns the node on which this line ends"
        pass

    @property
    @abstractmethod
    def frc(self) -> FRC:
        "Returns the functional road class of this line"
        pass

    @property
    @abstractmethod
    def fow(self) -> FOW:
        "Returns the form of way of this line"
        pass

    @abstractmethod
    def coordinates(self) -> Iterable[Coordinates]:
        """Returns the shape of the line.
        Yields GeoCoordinate values."""
        pass

    @property
    def length(self) -> float:
        """Based on the segments, returns the line length in meters

        Overwrite if you want to measure it in a different way"""
        points = list(self.coordinates)
        return sum(a.distance(b) for (a, b) in zip(points, points[1:]))

    @abstractmethod
    def distance_to(self, coord: Coordinates) -> int:
        "Compute the point-to-line distance"
        pass

class Node(ABC):
    "Abstract class modelling a node returned by a map reader"

    @property
    @abstractmethod
    def coordinates(self) -> Coordinates:
        "Returns the position of this node as lon, lat"
        pass

    @abstractmethod
    def outgoing_lines(self) -> Iterable[Line]:
        "Yields all lines coming directly from this node"
        pass

    @abstractmethod
    def incoming_lines(self) -> Iterable[Line]:
        "Yields all lines coming directly to this node."
        pass

    @abstractmethod
    def connected_lines(self) -> Iterable[Line]:
        "Returns lines which touch this node"
        pass

    @property
    @abstractmethod
    def node_id(self) -> Hashable:
        "Returns the id of this node."
        pass

class MapReader(ABC):
    """Abstract base class for map readers.

    This is an adapter class that fulfills the map requirements of OpenLR."""
    @abstractmethod
    def get_line(self, line_id: Hashable) -> Line:
        "Returns a line by its id"
        pass

    @abstractmethod
    def get_lines(self) -> Iterable[Line]:
        "Yields all lines in the map."
        pass

    @abstractmethod
    def get_linecount(self) -> int:
        "Returns the number of lines in the map."
        pass

    @abstractmethod
    def get_node(self, node_id: Hashable) -> Node:
        "Returns a node by its id."
        pass

    @abstractmethod
    def get_nodes(self) -> Iterable[Node]:
        "Yields all nodes contained in the map."
        pass

    @abstractmethod
    def get_nodecount(self) -> int:
        "Returns the number of nodes in the map."
        pass

    @abstractmethod
    def find_nodes_close_to(self, coord: Coordinates, dist: float) -> Iterable[Node]:
        """Iterates over all nodes in radius `distance` around `coord`.

        No order specified here."""
        pass

    @abstractmethod
    def find_lines_close_to(self, coord: Coordinates, dist: float) -> Iterable[Line]:
        """Iterates over all lines in radius `distance` around `coord`.

        No order specified here."""
        pass

def path_length(lines: Iterable[Line]) -> float:
    "Length of a path in the map, in meters"
    return sum([line.length for line in lines])
