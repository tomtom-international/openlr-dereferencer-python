"""An abstract `MapReader` base class, which must be implemented for each
map format to decode location references on."""
from abc import ABC, abstractmethod
from typing import Iterable, Hashable, Sequence
from openlr import Coordinates, FOW, FRC
from shapely.geometry import LineString, Point
from shapely.geometry.base import BaseGeometry

class GeometricObject(ABC):
    @property
    @abstractmethod
    def geometry(self) -> BaseGeometry:
        "Returns the geometry of this object"

class Line(GeometricObject):
    "Abstract Line class, modelling a line coming from a map reader"

    @property
    @abstractmethod
    def line_id(self) -> Hashable:
        "Returns the id of the line. A type is not specified here."

    @property
    @abstractmethod
    def start_node(self) -> "Node":
        "Returns the node from which this line starts"

    @property
    @abstractmethod
    def end_node(self) -> "Node":
        "Returns the node on which this line ends"

    @property
    @abstractmethod
    def frc(self) -> FRC:
        "Returns the functional road class of this line"

    @property
    @abstractmethod
    def fow(self) -> FOW:
        "Returns the form of way of this line"

    @property
    @abstractmethod
    def geometry(self) -> LineString:
        "Returns the geometric shape as a linestring"

    def coordinates(self) -> Sequence[Coordinates]:
        """Returns the shape of the line as list of Coordinates"""
        return [Coordinates(*point) for point in self.geometry.coords]

    @property
    def length(self) -> float:
        "Return the line length in meters"

    @abstractmethod
    def distance_to(self, coord: Coordinates) -> int:
        "Compute the point-to-line distance"


class Node(GeometricObject):
    "Abstract class modelling a node returned by a map reader"

    @property
    @abstractmethod
    def coordinates(self) -> Coordinates:
        "Returns the lon, lat coordinates of this node"

    @property
    def geometry(self) -> Point:
        "Returns the position of this node as shapely point"
        return Point(*self.coordinates)

    @abstractmethod
    def outgoing_lines(self) -> Iterable[Line]:
        "Yields all lines coming directly from this node"

    @abstractmethod
    def incoming_lines(self) -> Iterable[Line]:
        "Yields all lines coming directly to this node."

    @abstractmethod
    def connected_lines(self) -> Iterable[Line]:
        "Returns lines which touch this node"

    @property
    @abstractmethod
    def node_id(self) -> Hashable:
        "Returns the id of this node."


class MapReader(ABC):
    """Abstract base class for map readers.

    This is an adapter class that fulfills the map requirements of OpenLR."""

    @abstractmethod
    def get_line(self, line_id: Hashable) -> Line:
        "Returns a line by its id"

    @abstractmethod
    def get_lines(self) -> Iterable[Line]:
        "Yields all lines in the map."

    @abstractmethod
    def get_linecount(self) -> int:
        "Returns the number of lines in the map."

    @abstractmethod
    def get_node(self, node_id: Hashable) -> Node:
        "Returns a node by its id."

    @abstractmethod
    def get_nodes(self) -> Iterable[Node]:
        "Yields all nodes contained in the map."

    @abstractmethod
    def get_nodecount(self) -> int:
        "Returns the number of nodes in the map."

    @abstractmethod
    def find_nodes_close_to(self, coord: Coordinates, dist: float) -> Iterable[Node]:
        """Iterates over all nodes within `dist` meters around `coord`.

        No order specified here."""

    @abstractmethod
    def find_lines_close_to(self, coord: Coordinates, dist: float) -> Iterable[Line]:
        """Iterates over all lines within `dist` meters around `coord`.

        No order specified here."""


def path_length(lines: Iterable[Line]) -> float:
    "Length of a path in the map, in meters"
    return sum([line.length for line in lines])
