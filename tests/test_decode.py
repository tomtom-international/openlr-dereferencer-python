"Contains the unit tests for the decoding logic"
import unittest
from itertools import zip_longest
from typing import List, Iterable, TypeVar

from openlr import Coordinates, FRC, FOW, LineLocation as LineLocationRef, \
    LocationReferencePoint, PointAlongLineLocation, Orientation, SideOfRoad
from openlr_dereferencer.decoding import decode, LineLocation, PointAlongLine, LRDecodeError
from openlr_dereferencer.decoding.candidates import generate_candidates
from openlr_dereferencer.decoding.scoring import score_geolocation, score_frc, score_fow, \
    score_bearing, score_angle_difference
from openlr_dereferencer.example_sqlite_map import ExampleMapReader
from openlr_dereferencer.maps.wgs84 import distance, bearing

from .example_mapformat import setup_testdb, remove_db_file

class DummyNode():
    "Fake Node class for unit testing"
    def __init__(self, coord: Coordinates):
        self.coord = coord

    def __str__(self) -> str:
        return f"Node at {self.coord}"

    @property
    def coordinates(self) -> Coordinates:
        "Return the saved coordinates"
        return self.coord

class DummyLine():
    "Fake Line class for unit testing"
    def __init__(self, l_id, start: DummyNode, end: DummyNode):
        self.line_id = l_id
        self.start_node = start
        self.end_node = end

    def __str__(self) -> str:
        return (
            f"Line with id {self.line_id} and length {self.length} "
            f"from {self.start_node.coord} to {self.end_node.coord}"
        )

    def coordinates(self) -> List[Coordinates]:
        "Returns a list of this line's coordinates"
        return [self.start_node.coord, self.end_node.coord]

    @property
    def length(self) -> float:
        "Return distance between star and end node"
        return distance(self.start_node.coord, self.end_node.coord)

def get_test_linelocation_1():
    "Return a prepared line location with 3 LRPs"
    # References node 0 / line 1 / lines 1, 3
    lrp1 = LocationReferencePoint(13.41, 52.525,
                                  FRC.FRC0, FOW.SINGLE_CARRIAGEWAY, 0.75,
                                  FRC.FRC2, 837.0)
    # References node 3 / line 4
    lrp2 = LocationReferencePoint(13.4145, 52.529,
                                  FRC.FRC2, FOW.SINGLE_CARRIAGEWAY, 0.0,
                                  FRC.FRC2, 456.6)
    # References node 4 / line 4
    lrp3 = LocationReferencePoint(13.416, 52.525, FRC.FRC2,
                                  FOW.SINGLE_CARRIAGEWAY, 0.125, None, None)
    return LineLocationRef([lrp1, lrp2, lrp3], 0.0, 0.0)

def get_test_pointalongline() -> PointAlongLineLocation:
    "Get a test Point Along Line location reference"
    path_ref = get_test_linelocation_1().points[1:]
    return PointAlongLineLocation(path_ref, 0.5, Orientation.WITH_LINE_DIRECTION, \
                                  SideOfRoad.RIGHT)
    
def get_test_invalid_pointalongline() -> PointAlongLineLocation:
    "Get a test Point Along Line location reference"
    path_ref = get_test_linelocation_1().points[-2:]
    return PointAlongLineLocation(path_ref, 1.5, Orientation.WITH_LINE_DIRECTION, \
                                  SideOfRoad.RIGHT)

T = TypeVar("T")

class DecodingTests(unittest.TestCase):
    "Unittests for the decoding logic"
    db = 'db.sqlite'

    def assertIterableAlmostEqual(self, iter_a: Iterable[T], iter_b: Iterable[T], delta: float):
        """Tests if `a` and `b` iterate over nearly-equal floats.

        This means, that two floats of the same index in `a` and `b` should not have a greater
        difference than `delta`."""
        # Get the generators
        gen_a = iter(iter_a)
        gen_b = iter(iter_b)
        for (a, b) in zip_longest(gen_a, gen_b):
            if abs(a - b) > delta:
                list_a = [a] + list(gen_a)
                list_b = [b] + list(gen_b)
                msg = (f"Iterables are not almost equal within delta {delta}.\n"
                       f"Remaining a: {list_a}\nRemaining b: {list_b}")
                raise self.failureException(msg)

    def setUp(self):
        remove_db_file(self.db)
        setup_testdb(self.db)
        self.reader = ExampleMapReader(self.db)

    def test_geoscore_1(self):
        "Test scoring an excactly matching LRP candidate line"
        lrp = LocationReferencePoint(0.0, 0.0, None, None, None, None, None)
        node1 = DummyNode(Coordinates(0.0, 0.0))
        node2 = DummyNode(Coordinates(0.0, 90.0))
        score = score_geolocation(lrp, DummyLine(None, node1, node2), 1.0, False)
        self.assertEqual(score, 1.0)

    def test_geoscore_0(self):
        "Test scoring a non-matching LRP candidate line"
        lrp = LocationReferencePoint(0.0, 0.0, None, None, None, None, None)
        node1 = DummyNode(Coordinates(0.0, 0.0))
        node2 = DummyNode(Coordinates(0.0, 90.0))
        score = score_geolocation(lrp, DummyLine(None, node1, node2), 1.0, True)
        self.assertEqual(score, 0.0)

    def test_frcscore_0(self):
        "Test scoring two non-matching FRCs"
        frc_a = FRC.FRC0
        frc_b = FRC.FRC7
        self.assertEqual(score_frc(frc_a, frc_b), 0.0)
        self.assertEqual(score_frc(frc_b, frc_a), 0.0)

    def test_frcscore_1(self):
        "Test scoring two equal FRCs"
        frc = FRC.FRC0
        # If it would not be exactly 1.0, it would be weird
        self.assertEqual(score_frc(frc, frc), 1.0)

    def test_fowscore_0(self):
        "Test scoring two non-matching FOWs"
        fow_a = FOW.UNDEFINED
        fow_b = FOW.OTHER
        self.assertAlmostEqual(score_fow(fow_a, fow_b), 0.5)
        self.assertAlmostEqual(score_fow(fow_b, fow_a), 0.5)

    def test_fowscore_1(self):
        "Test scoring two equal FOWs"
        fow = FOW.MOTORWAY
        self.assertEqual(score_fow(fow, fow), 1.0)

    def test_bearingscore_1(self):
        "Test bearing difference of +90°"
        node1 = DummyNode(Coordinates(0.0, 0.0))
        node2 = DummyNode(Coordinates(0.0, 90.0))
        node3 = DummyNode(Coordinates(1.0, 0.0))
        wanted_bearing = bearing(node1.coordinates, node2.coordinates)
        wanted = LocationReferencePoint(13.416, 52.525, FRC.FRC2,
                                        FOW.SINGLE_CARRIAGEWAY, wanted_bearing, None, None)
        score = score_bearing(wanted, DummyLine(1, node1, node3), False)
        self.assertEqual(score, 0.5)

    def test_bearingscore_2(self):
        "Test bearing difference of -90°"
        node1 = DummyNode(Coordinates(0.0, 0.0))
        node2 = DummyNode(Coordinates(0.0, 90.0))
        node3 = DummyNode(Coordinates(-1.0, 0.0))
        wanted_bearing = bearing(node1.coordinates, node2.coordinates)
        wanted = LocationReferencePoint(13.416, 52.525, FRC.FRC2,
                                        FOW.SINGLE_CARRIAGEWAY, wanted_bearing, None, None)
        score = score_bearing(wanted, DummyLine(1, node1, node3), False)
        self.assertEqual(score, 0.5)

    def test_bearingscore_3(self):
        "Test the angle scoring function from 0"
        sub_testcases = [-360, -720, 0, 180, 540, 720]
        scores = map(lambda arc: score_angle_difference(0, arc), sub_testcases)
        self.assertIterableAlmostEqual([1.0, 1.0, 1.0, 0.0, 0.0, 1.0], list(scores), 0.001)

    def test_bearingscore_4(self):
        "Test the angle scoring function from 271°"
        sub_testcases = [-89, 91, 181, 226]
        scores = map(lambda arc: score_angle_difference(271, arc), sub_testcases)
        self.assertIterableAlmostEqual([1.0, 0.0, 0.5, 0.75], list(scores), 0.001)

    def test_generate_candidates_1(self):
        "Generate candidates and pick the best"
        reference = get_test_linelocation_1()
        candidates = list(generate_candidates(reference.points[0], self.reader, 40.0, False))
        # Sort by score
        candidates.sort(key=lambda candidate: candidate[1], reverse=True)
        # Get only the line ids
        candidates = [line.line_id for (line, score) in candidates]
        # Now assert the best
        self.assertEqual(candidates[0], 1)

    def test_decode_3_lrps(self):
        "Decode a line location of 3 LRPs"
        reference = get_test_linelocation_1()
        location = decode(reference, self.reader, 15.0)
        self.assertTrue(location, LineLocation)
        lines = [l.line_id for l in location.lines]
        self.assertListEqual([1, 3, 4], lines)
        self.assertListEqual(location.coordinates(),
                             [Coordinates(13.41, 52.525), Coordinates(13.414, 52.525),
                              Coordinates(13.4145, 52.529), Coordinates(13.416, 52.525)])

    def test_decode_offsets(self):
        "Decode a line location with offsets"
        reference = get_test_linelocation_1()
        reference = reference._replace(poffs=0.25)
        reference = reference._replace(noffs=0.75)
        path = decode(reference, self.reader, 15.0).coordinates()
        self.assertTrue(path, LineLocation)
        self.assertEqual(len(path), 4)
        self.assertAlmostEqual(path[0].lon, 13.414, delta=0.001)
        self.assertAlmostEqual(path[0].lat, 52.525, delta=0.001)
        self.assertAlmostEqual(path[1].lon, 13.414, delta=0.001)
        self.assertAlmostEqual(path[1].lat, 52.525, delta=0.001)

    def test_decode_pointalongline(self):
        "Test a valid point along line location"
        # Get a list of 2 LRPs
        reference = get_test_pointalongline()
        pal: PointAlongLine = decode(reference, self.reader)
        coords = pal.coordinates()
        self.assertAlmostEqual(coords.lon, 13.4153, delta=0.0001)
        self.assertAlmostEqual(coords.lat, 52.5270, delta=0.0001)

    def test_decode_pointalong_raises(self):
        "Test an invalid point along line location with too high offset"
        # Get a list of 2 LRPs
        reference = get_test_invalid_pointalongline()
        with self.assertRaises(LRDecodeError):
            decode(reference, self.reader)

    def tearDown(self):
        self.reader.connection.close()
        remove_db_file(self.db)
