"Some tooling functions for path and offset handling"

from typing import List, Tuple
from logging import debug
from openlr import Coordinates, LocationReferencePoint
from ..maps import Line
from ..maps.wgs84 import project_along_path


def add_offsets(path: List[Line], p_off: float, n_off: float) -> List[Coordinates]:
    "Add the absolute meter offsets to `path` and return the resulting coordinate list"
    coordinates = [path[0].start_node.coordinates]
    for line in path:
        coordinates.append(line.end_node.coordinates)
    # If offsets available, correct first / last coordinate
    if p_off > 0.0:
        # first LRP to second one
        coordinates[0] = project_along_path(coordinates, p_off)
    if n_off > 0.0:
        # last LRP to second-last LRP
        coordinates[-1] = project_along_path(coordinates[::-1], n_off)
    return coordinates


def remove_unnecessary_lines(
    path: List[Line], p_off: float, n_off: float
) -> Tuple[List[Line], float, float]:
    """Remove start+end lines shorter than the offset and adjust offsets accordingly

    If the offsets are greater than the first/last line, remove that line from the path.

    Reason: The location reference path may be longer than the line location path
    (which this function has to return)"""
    resulting_path = path[:]
    while resulting_path[0].length < p_off:
        p_off -= resulting_path[0].length
        debug(f"removing {resulting_path[0]} because p_off is {p_off}")
        resulting_path.pop(0)
    while resulting_path[-1].length < n_off:
        n_off -= resulting_path[-1].length
        debug(f"removing {resulting_path[-1]} because n_off is {n_off}")
        resulting_path.pop()
    debug(f"path[n-1] ({resulting_path[-1]}) seems to be longer than n_off {n_off}")
    return resulting_path, p_off, n_off


class LRDecodeError(Exception):
    "An error that happens through decoding location references"


def coords(lrp: LocationReferencePoint) -> Coordinates:
    "Return the coordinates of an LRP"
    return Coordinates(lrp.lon, lrp.lat)
