"Contains the Node and the Line class of the example format"
from collections import namedtuple
from itertools import chain
import functools
from typing import Iterable
from openlr import Coordinates, FRC, FOW
from shapely.geometry import LineString
from shapely import wkt
from openlr_dereferencer.maps import Line as AbstractLine, Node as AbstractNode

LineNode = namedtuple("LineNode", ["start_node", "end_node"])


class Line(AbstractLine):
    "Line object implementation for the example format"

    def __init__(self, map_reader, line_id: int):
        if not isinstance(line_id, int):
            raise ExampleMapError(f"Line id '{line_id}' has confusing type {type(line_id)}")
        self.map_reader = map_reader
        self.db_schema = map_reader.db_schema
        self.lines_tbl_name = map_reader.lines_tbl_name
        self.nodes_tbl_name = map_reader.nodes_tbl_name
        self.line_id_internal = line_id
        self.srid = map_reader.srid
        self._start_node = None
        self._end_node = None
        self._fow = None
        self._frc = None
        self._geometry = None
        self._numpoints = None
        self._length = None

    def __repr__(self):
        return f"Line with id={self.line_id} of length {self.length}"

    @property
    def line_id(self) -> int:
        "Returns the line id"
        return self.line_id_internal

    def get_and_store_database_info(self):
        stmt = f"""
            SELECT 
                startnode,
                endnode,
                fow,
                frc,
                ST_astext(geometry),
                ST_NumPoints(geometry),
                st_length(geometry)
            FROM {self.db_schema}.{self.lines_tbl_name}
            WHERE line_id = %s
        """
        self.map_reader.cursor.execute(stmt, (self.line_id,))
        (startnode, endnode, fow, frc, geometry, num_points, length) = self.map_reader.cursor.fetchone()
        self._start_node = Node(self.map_reader, startnode)
        self._end_node = Node(self.map_reader, endnode)
        self._fow = FOW(fow)
        self._frc = FRC(frc)
        self._geometry = wkt.loads(geometry)
        self._numpoints = num_points
        self._length = length

    @property
    def start_node(self) -> "Node":
        "Returns the node from which this line comes from"
        if not self._start_node:
            self.get_and_store_database_info()
        return self._start_node

    @property
    def end_node(self) -> "Node":
        "Returns the node to which this line goes"
        if not self._end_node:
            self.get_and_store_database_info()
        return self._end_node

    @property
    def fow(self) -> FOW:
        "Returns the form of way for this line"
        if not self._fow:
            self.get_and_store_database_info()
        return self._fow

    @property
    def frc(self) -> FRC:
        "Returns the functional road class for this line"
        if not self._frc:
            self.get_and_store_database_info()
        return self._frc

    @property
    def length(self) -> float:
        "Length of line in meters"
        if not self._length:
            self.get_and_store_database_info()
        return self._length

    @property
    def geometry(self) -> LineString:
        "Returns the line geometry"
        # chg list comp to single call
        if not self._geometry:
            self.get_and_store_database_info()
        return self._geometry

    def num_points(self) -> int:
        "Returns how many points the path geometry contains"
        if not self._numpoints:
            self.get_and_store_database_info()
        return self._numpoints

    def distance_to(self, coord) -> float:
        "Returns the distance of this line to `coord` in meters"
        stmt = f"""
            SELECT
                ST_Distance(
                    ST_SetSRID(ST_MakePoint(%s,%s), {self.srid}),
                    geometry
                )
            FROM {self.db_schema}.{self.lines_tbl_name} 
            WHERE
                line_id = %s;
        """
        cur = self.map_reader.cursor
        cur.execute(stmt, (coord.lon, coord.lat, self.line_id))
        (dist,) = cur.fetchone()
        if dist is None:
            return 0.0
        return dist

    def point_n(self, index) -> Coordinates:
        "Returns the `n` th point in the path geometry, starting at 0"
        stmt = f"""
        SELECT ST_X(ST_PointN(geometry, %s)), ST_Y(ST_PointN(geometry, %s))
        FROM {self.db_schema}.{self.lines_tbl_name}
        WHERE line_id = %s
        """
        self.map_reader.cursor.execute(stmt, (index, index, self.line_id))
        (lon, lat) = self.map_reader.cursor.fetchone()
        if lon is None or lat is None:
            raise Exception(f"line {self.line_id} has no point {index}!")
        return Coordinates(lon, lat)

    def near_nodes(self, distance):
        "Yields every point within a certain distance, in meters."
        stmt = f"""
            SELECT
                nodes.node_id
            FROM {self.db_schema}.{self.nodes_tbl_name} nodes, {self.db_schema}.{self.lines_tbl_name} lines
            WHERE
                lines.line_id = %s AND 
                ST_DWithin(
                    nodes.geometry,
                    lines.geometry,
                    %s
                )
        """
        self.map_reader.cursor.execute(stmt, (self.line_id, distance))
        for (point_id,) in self.map_reader.cursor.fetchall():
            yield self.map_reader.get_node(point_id)


class Node(AbstractNode):
    "Node class implementation for example_postgres_map"

    def __init__(self, map_reader, node_id: int):
        if not isinstance(node_id, int):
            raise ExampleMapError(f"Node id '{id}' has confusing type {type(node_id)}")
        self.map_reader = map_reader
        self.db_schema = map_reader.db_schema
        self.lines_tbl_name = map_reader.lines_tbl_name
        self.nodes_tbl_name = map_reader.nodes_tbl_name
        self.node_id_internal = node_id

    @property
    def node_id(self):
        return self.node_id_internal

    @property
    def coordinates(self) -> Coordinates:
        stmt = f"SELECT ST_X(geometry), ST_Y(geometry) FROM {self.db_schema}.{self.nodes_tbl_name} WHERE node_id = %s"
        self.map_reader.cursor.execute(stmt, (self.node_id,))
        geo = self.map_reader.cursor.fetchone()
        return Coordinates(lon=geo[0], lat=geo[1])

    @functools.cache
    def outgoing_lines(self) -> Iterable[Line]:
        stmt = f"SELECT line_id FROM {self.db_schema}.{self.lines_tbl_name} WHERE startnode = %s"
        self.map_reader.cursor.execute(stmt, (self.node_id,))
        return [Line(self.map_reader, line_id[0]) for line_id in self.map_reader.cursor.fetchall()]

    @functools.cache
    def incoming_lines(self) -> Iterable[Line]:
        stmt = f"SELECT line_id FROM {self.db_schema}.{self.lines_tbl_name} WHERE endnode = %s"
        self.map_reader.cursor.execute(stmt, [self.node_id])
        return [Line(self.map_reader, line_id[0]) for line_id in self.map_reader.cursor.fetchall()]

    @functools.cache
    def incoming_line_nodes(self) -> Iterable[LineNode]:
        stmt = f"SELECT startnode, endnode FROM {self.db_schema}.{self.lines_tbl_name} WHERE startnode = %s"
        self.map_reader.cursor.execute(stmt, (self.node_id,))
        return [
            LineNode(Node(self.map_reader, startnode), Node(self.map_reader, endnode))
            for startnode, endnode in self.map_reader.cursor.fetchall()
        ]

    @functools.cache
    def outgoing_line_nodes(self) -> Iterable[LineNode]:
        stmt = f"SELECT startnode, endnode FROM {self.db_schema}.{self.lines_tbl_name} WHERE endnode = %s"
        self.map_reader.cursor.execute(stmt, (self.node_id,))
        return [
            LineNode(Node(self.map_reader, startnode), Node(self.map_reader, endnode))
            for startnode, endnode in self.map_reader.cursor.fetchall()
        ]

    def connected_lines(self) -> Iterable[Line]:
        return chain(self.incoming_lines(), self.outgoing_lines())


class ExampleMapError(Exception):
    "Some error reading the DB"
