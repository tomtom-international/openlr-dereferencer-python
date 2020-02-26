"""Scoring functions and default weights for candidate line rating

FOW_WEIGHT + FRC_WEIGHT + GEO_WEIGHT + BEAR_WEIGHT should always be `1`.

The result of the scoring functions will be floats from 0.0 to 1.0,
with `1.0` being an exact match and 0.0 being a non-match."""

from math import degrees
from logging import debug
from openlr import Coordinates, FRC, FOW, LocationReferencePoint
from ..maps.wgs84 import project_along_path, distance, bearing
from ..maps import Line
from .tools import coords

FOW_WEIGHT = 1 / 4
FRC_WEIGHT = 1 / 4
GEO_WEIGHT = 1 / 4
BEAR_WEIGHT = 1 / 4

BEAR_DIST = 20

# When comparing an LRP FOW with a candidate's FOW, this matrix defines
# how well the candidate's FOW fits as replacement for the expected value.
# The usage is `FOW_SCORING[lrp's fow][candidate's fow]`.
# It returns the score.
# The values are adopted from the openlr Java implementation.
FOW_STAND_IN_SCORE = [
    [0.50, 0.50, 0.50, 0.50, 0.50, 0.50, 0.50, 0.5],  # Undefined FOW
    [0.50, 1.00, 0.75, 0.00, 0.00, 0.00, 0.00, 0.0],  # Motorway
    [0.50, 0.75, 1.00, 0.75, 0.50, 0.00, 0.00, 0.0],  # Multiple carriage way
    [0.50, 0.00, 0.75, 1.00, 0.50, 0.50, 0.00, 0.0],  # Single carriage way
    [0.50, 0.00, 0.50, 0.50, 1.00, 0.50, 0.00, 0.0],  # Roundabout
    [0.50, 0.00, 0.00, 0.50, 0.50, 1.00, 0.00, 0.0],  # Traffic quare
    [0.50, 0.00, 0.00, 0.00, 0.00, 0.00, 1.00, 0.0],  # Sliproad
    [0.50, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 1.0],  # Other FOW
]

# LocationReferencePoint.bear is angle / 11.25°, so has to be multiplied to get the degree value
BEAR_MULTIPLIER = 11.25


def score_fow(wanted: FOW, actual: FOW) -> float:
    "Return a score for a FOW value"
    return FOW_STAND_IN_SCORE[wanted][actual]


def score_frc(wanted: FRC, actual: FRC) -> float:
    "Return a score for a FRC value"
    return 1.0 - abs(actual - wanted) / 7


def score_geolocation(
    wanted: LocationReferencePoint, actual: Line, radius: float, is_last_lrp: bool
) -> float:
    """Scores the geolocation of a candidate.

    A distance of `radius` or more will result in a 0.0 score."""
    if is_last_lrp:
        actual_point = actual.end_node.coordinates
    else:
        actual_point = actual.start_node.coordinates
    dist = distance(coords(wanted), actual_point)
    if dist < radius:
        return 1.0 - dist / radius
    return 0.0


def get_bearing_point(candidate: Line, reverse: bool = False) -> Coordinates:
    "Gets the point to which the bearing angle is computed."
    if candidate.length < BEAR_DIST:
        return candidate.end_node.coordinates
    coordinates = list(candidate.coordinates())
    if reverse:
        coordinates.reverse()
    return project_along_path(coordinates, BEAR_DIST)


def score_angle_difference(angle1: float, angle2: float) -> float:
    """Helper for `score_bearing` which scores the angle difference.

    Args:
        angle1, angle2: angles, in degrees.
    Returns:
        The similarity of angle1 and angle2, from 0.0 (180° difference) to 1.0 (0° difference)
    """
    difference = (abs(angle1 - angle2) + 180) % 360 - 180
    return 1 - abs(difference) / 180


def score_bearing(wanted: LocationReferencePoint, candidate: Line, is_last_lrp: bool) -> float:
    """Scores the difference between expected and actual bearing angle.

    A difference of 0° will result in a 1.0 score, while 180° will cause a score of 0.0."""
    point1 = candidate.start_node.coordinates
    point2 = get_bearing_point(candidate)
    bear = degrees(bearing(point1, point2))
    expected_bearing = BEAR_MULTIPLIER * wanted.bear
    if is_last_lrp:
        return score_angle_difference(expected_bearing, bear - 180)
    return score_angle_difference(expected_bearing, bear)


def score_lrp_candidate(
    wanted: LocationReferencePoint, candidate: Line, radius: float, is_last_lrp: bool
) -> float:
    """Scores the candidate (line) for the LRP.

    This is the average of fow, frc, geo and bearing score."""
    score = (
        FOW_WEIGHT * score_fow(wanted.fow, candidate.fow)
        + FRC_WEIGHT * score_frc(wanted.frc, candidate.frc)
        + GEO_WEIGHT * score_geolocation(wanted, candidate, radius, is_last_lrp)
        + BEAR_WEIGHT * score_bearing(wanted, candidate, is_last_lrp)
    )
    debug(f"scoring line {candidate.line_id}")
    debug(f"geo score: {score_geolocation(wanted, candidate, radius, is_last_lrp)}")
    debug(f"fow score: {score_fow(wanted.fow, candidate.fow)}")
    debug(f"frc score: {score_frc(wanted.frc, candidate.frc)}")
    debug(f"bearing score: {score_bearing(wanted, candidate, is_last_lrp)}")
    debug(f"total score: {score}")
    return score
