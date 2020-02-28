"""The example map format described in `map_format.md`, conforming to
the interface in openlr_dereferencer.maps"""

import os
import sqlite3
from typing import Sequence, Tuple, Iterable
from openlr import Coordinates
from .primitives import Line, Node, ExampleMapError, SRID
from ..maps import MapReader, wgs84


class ExampleMapReader(MapReader):
    """
    This is a reader for the example map format described in `map_format.md`.

    Create an instance with: `ExampleMapReader('example.sqlite')`.
    """

    def __init__(self, map_db_file: str):
        self.connection = sqlite3.connect(map_db_file)
        self.connection.enable_load_extension(True)
        try:
            self.connection.load_extension("mod_spatialite.so")
        except sqlite3.OperationalError:
            raise ExampleMapError(
                "Spatialite (mod_spatialite.so) was not found on your system."
                "Please install all dependencies."
            )

    def get_line(self, line_id: int) -> Line:
        # Just verify that this line ID exists.
        result = self.connection.execute("SELECT rowid FROM lines WHERE rowid=?", (line_id,))
        if result.fetchone() is None:
            raise ExampleMapError(f"The line {line_id} does not exist")
        return Line(self, line_id)

    def get_lines(self) -> Iterable[Line]:
        result = self.connection.execute("SELECT rowid FROM lines")
        for (line_id,) in result:
            yield Line(self, line_id)

    def get_linecount(self) -> int:
        (count,) = self.connection.execute("SELECT COUNT(*) FROM lines").fetchone()
        return count

    def get_node(self, node_id: int) -> Node:
        result = self.connection.execute("SELECT id FROM nodes WHERE id=?", (node_id,))
        (node_id,) = result.fetchone()
        return Node(self, node_id)

    def get_nodes(self) -> Iterable[Node]:
        result = self.connection.execute("SELECT id FROM nodes")
        for (node_id,) in result.fetchall():
            yield Node(self, node_id)

    def get_nodecount(self) -> int:
        (count,) = self.connection.execute("SELECT COUNT(*) FROM nodes").fetchone()
        return count

    def find_nodes_close_to(self, coord: Coordinates, dist: float) -> Iterable[Node]:
        """Finds all nodes in a given radius, given in meters

        Yields every node with its meter distance to `coord`."""
        lon, lat = coord.lon, coord.lat
        stmt = """SELECT id FROM nodes WHERE Distance(MakePoint(?, ?), coord, 1) < ?"""
        for (node_id,) in self.connection.execute(stmt, (lon, lat, dist)):
            yield Node(self, node_id)

    def find_lines_close_to(self, coord: Coordinates, dist: float) -> Iterable[Line]:
        "Yields all lines in a given radius"
        lon, lat = coord.lon, coord.lat
        stmt = """SELECT rowid FROM lines WHERE Distance(MakePoint(?, ?), path) < ?"""
        for (line_id,) in self.connection.execute(stmt, (lon, lat, dist)):
            yield Line(self, line_id)
