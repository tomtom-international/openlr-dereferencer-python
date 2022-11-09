"""The example map format described in `map_format.md`, conforming to
the interface in openlr_dereferencer.maps"""

import os
import psycopg2
from typing import Sequence, Tuple, Iterable
from openlr import Coordinates
from .primitives import Line, Node, ExampleMapError
from ..maps import MapReader, wgs84


class PostgresMapReader(MapReader):
    """
    This is a reader for the example map format described in `map_format.md`.

    Create an instance with: `ExampleMapReader('example.sqlite')`.
    """,

    def __init__(self,user,password,dbname):
        self.connection = psycopg2.connect(
            host="localhost",
            port=5432,
            user=user,
            password=password,
            dbname=dbname,
            connect_timeout=10,
            options="-c statement_timeout=20000",
            application_name="openlr",
        )
        self.cursor = self.connection.cursor()

    def get_line(self, line_id: int) -> Line:
        # Just verify that this line ID exists.
        self.cursor.execute("SELECT line_id FROM openlr_lines WHERE line_id=%s", (line_id,))
        if self.cursor.fetchone() is None:
            raise ExampleMapError(f"The line {line_id} does not exist")
        return Line(self, line_id)

    def get_lines(self) -> Iterable[Line]:
        self.cursor.execute("SELECT line_id FROM openlr_lines")
        for (line_id,) in self.cursor.fetchall():
            yield Line(self, line_id)

    def get_linecount(self) -> int:
        self.cursor.execute("SELECT COUNT(*) FROM openlr_lines")
        (count,) = self.cursor.fetchone()
        return count

    def get_node(self, node_id: int) -> Node:
        self.cursor.execute("SELECT node_id FROM openlr_nodes WHERE node_id=%s", (node_id,))
        (node_id,) = self.cursor.fetchone()
        return Node(self, node_id)

    def get_nodes(self) -> Iterable[Node]:
        self.cursor.execute("SELECT node_id FROM openlr_nodes")
        for (node_id,) in self.cursor.fetchall():
            yield Node(self, node_id)

    def get_nodecount(self) -> int:
        self.cursor.execute("SELECT COUNT(*) FROM openlr_nodes")
        (count,) = self.cursor.fetchone()
        return count

    def find_nodes_close_to(self, coord: Coordinates, dist: float) -> Iterable[Node]:
        """Finds all nodes in a given radius, given in meters
        print("Node",coord, dist)
        Yields every node within this distance to `coord`."""
        lon, lat = coord.lon, coord.lat
        stmt = """
            SELECT
                node_id
            FROM openlr_nodes 
            WHERE ST_Distance(
                ST_SetSRID(ST_MakePoint(%s,%s),4326)::geography, 
                coord::geography
            ) < %s;
        """
        self.cursor.execute(stmt, (lon, lat, dist))
        for (node_id,) in self.cursor.fetchall():
            print("Node",coord, dist, node_id)
            yield Node(self, node_id)

    def find_lines_close_to(self, coord: Coordinates, dist: float) -> Iterable[Line]:
        "Yields all lines within `dist` meters around `coord`"
        print("Line",coord, dist)
        lon, lat = coord.lon, coord.lat
        stmt = """
            SELECT
                line_id
            FROM openlr_lines 
            WHERE ST_Distance(
                ST_SetSRID(ST_MakePoint(%s,%s),4326)::geography, 
                path::geography
            ) < %s;
        """
        self.cursor.execute(stmt, (lon, lat, dist))
        for (line_id,) in self.cursor.fetchall():
            print("Line",coord, dist, line_id)
            yield Line(self, line_id)
