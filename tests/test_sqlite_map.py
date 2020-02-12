"""
Contains the test DB data and the unittest for the example map format.
Dependency: apt install sqlite3 libsqlite3-mod-spatialite"""

import unittest

from openlr import Coordinates

from openlr_dereferencer.example_sqlite_map import ExampleMapReader

from .example_mapformat import setup_testdb, remove_db_file

class SQLiteMapTest(unittest.TestCase):
    "A few unit tests for the example sqlite mapformat"
    db = 'db.sqlite'

    def setUp(self):
        remove_db_file(self.db)
        setup_testdb(self.db)
        self.reader = ExampleMapReader(self.db)

    def test_line_length(self):
        "Check the length of the line with ID 1"
        line = self.reader.get_line(1)
        self.assertAlmostEqual(line.length, 391, delta=1)

    def test_linepoints(self):
        "Test the point count of every line"
        for line in self.reader.get_lines():
            self.assertEqual(line.num_points(), 2)

    def test_nearest(self):
        "Test the find_nodes_close_to with a manually chosen location"
        nodes = []
        nodes = [node.node_id for node \
            in self.reader.find_nodes_close_to(Coordinates(13.41, 52.523), 500)]
        self.assertSequenceEqual(nodes, [0, 1, 2, 4])

    def test_line_enumeration(self):
        "Test if a sorted list of line IDs is as expected"
        lines = []
        lines = [line.line_id for line in self.reader.get_lines()]
        self.assertEqual(len(lines), 17)
        self.assertSequenceEqual(sorted(lines), range(1, 18))

    def test_get_line(self):
        "Get a test line"
        _line = self.reader.get_line(17)

    def test_node_enumeration(self):
        "Test if a sorted list of point IDs is as expected"
        nodes = []
        nodes = [node.node_id for node in self.reader.get_nodes()]
        self.assertEqual(len(nodes), 14)
        self.assertSequenceEqual(sorted(nodes), range(14))

    def tearDown(self):
        self.reader.connection.close()
        remove_db_file(self.db)
