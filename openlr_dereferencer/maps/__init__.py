"""
This module describes the handling of maps. It provides an interface
through which the decoder accesses the map.
"""

from .abstract import MapReader, Line, Node, path_length
from .a_star import shortest_path
