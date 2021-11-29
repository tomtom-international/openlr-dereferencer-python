"Contains a testcase for the maps.a_star module"

import unittest

from openlr_dereferencer.maps import shortest_path
from openlr_dereferencer.example_sqlite_map import ExampleMapReader

from .example_mapformat import setup_testdb_in_memory, remove_db_file

class AStarTests(unittest.TestCase):
    "Tests the A* module"

    def setUp(self):
        self.reader = ExampleMapReader(":memory:")
        self.reader.connection = setup_testdb_in_memory()

    def test_shortest_path_same_node(self):
        "Shortest path between a node and itself is empty"
        point_a = self.reader.get_node(0)
        path = shortest_path(point_a, point_a)
        self.assertIsNotNone(path)
        self.assertSequenceEqual(path, [])

    def test_shortest_path_oneline(self):
        "Shortest path where the path is one line"
        point_a = self.reader.get_node(0)
        point_b = self.reader.get_node(2)
        path = shortest_path(point_a, point_b)
        self.assertIsNotNone(path)
        path = [line.line_id for line in path]
        self.assertSequenceEqual(path, [1])

    def test_shortest_path__lines_a(self):
        "More complex shortest path a"
        point_a = self.reader.get_node(1)
        point_b = self.reader.get_node(11)
        path = shortest_path(point_a, point_b)
        path = [line.line_id for line in path]
        self.assertSequenceEqual(path, [2, 5, 8, 14])

    def test_shortest_path__lines_b(self):
        "Shortest path where the path is two lines (b)"
        point_a = self.reader.get_node(0)
        point_b = self.reader.get_node(3)
        path = shortest_path(point_a, point_b)
        path = [line.line_id for line in path]
        self.assertSequenceEqual(path, [1, 3])

    def test_shortest_path__lines_c(self):
        "More complex shortest path c"
        point_a = self.reader.get_node(4)
        point_b = self.reader.get_node(9)
        path = shortest_path(point_a, point_b)
        path = [line.line_id for line in path]
        self.assertSequenceEqual(path, [8, 9, 10])

    def tearDown(self):
        self.reader.connection.close()
