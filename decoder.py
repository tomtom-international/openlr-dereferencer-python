"""
* This is a script intended to understand
the steps of a decoder and implications
on candidate selection

    - Inputs:
        - location references 
        - A target map
    - Outputs:
        - candidate traces of the decoder 
          to decode each input location reference (lr)
        - decoded locations for each lr
        - statistics on candidate traces with respect to input config
"""

from openlr_dereferencer import decoding
import argparse
import openlr
import openlr_sqlite_map
from openlr_dereferencer import decoding

import pdb

parser = argparse.ArgumentParser(
    description="Decode Location reference given target map"
)

parser.add_argument("map", type=str, help="path to target map")
parser.add_argument("lr", type=str, help=" location reference")

args = parser.parse_args()


# create map reader

def create_map_reader(map):
    database_reader = openlr_sqlite_map.create_database_reader(args.map)

    map_model = openlr_sqlite_map.MapModel(database_reader)

    map_reader = openlr_sqlite_map.DefaultMapReader(map_model)
    pdb.set_trace()
    return map_reader


# decode a lr on target map

def decode_lr(lr, target_map):

    """Decodes a location reference received as a base 64 string"""
    base64str = lr
    map_reader = create_map_reader(target_map)
    locref = None
    location = None

    try:
        locref = openlr.binary_decode(base64str)
        location = decoding.decode(locref, map_reader)
    except Exception:
        pass

    result = {
        "success": True if location else False,
        "locref": locref_dto(locref) if locref else None,
        "location": location_dto(location) if location else None,
    }

    # print("selected_candidate: ", location_dto(location))
    return location
    # pdb.set_trace()


def locref_dto(locref):
    """Builds a data object for a location reference"""
    if isinstance(locref, openlr.LineLocationReference):
        return line_locref_dto(locref)


def locref_dto(locref):
    """Builds a data object for a location reference"""
    if isinstance(locref, openlr.LineLocationReference):
        return line_locref_dto(locref)


def line_locref_dto(locref):
    """Builds a data object for a line location reference"""
    return {
        "lrps": [lrp_dto(point) for point in locref.points],
        "poff": locref.poffs,
        "noff": locref.noffs,
    }


def lrp_dto(point):
    """Builds a data object for a location reference point"""
    return {
        "coord": [point.lon, point.lat],
        "bearing": point.bear,
        "frc": point.frc,
        "fow": point.fow,
    }


def location_dto(location):
    """Builds a data object for a location"""
    if isinstance(location, decoding.LineLocation):
        return line_location_dto(location)


def line_location_dto(location):
    """Builds a data object for a line location"""
    return {
        "type": "Line",
        "lines": [line_dto(line) for line in location.lines],
        "coords": [[c.lon, c.lat] for c in location.coordinates()],
        "poff": location.p_off,
        "noff": location.n_off,
    }


def line_dto(line):
    """Builds a data object for a line"""
    return {
        "id": line.line_id.link_id,
        "forward": line.line_id.forward,
        "frc": line.frc,
        "fow": line.fow,
        "coords": [list(c) for c in line.geometry.coords],
    }


if __name__ == "__main__":

    decoded_location = decode_lr(args.lr, args.map)

    #print("selected_candidate: ", location_dto(decoded_location))
    # add inputs to decoder


