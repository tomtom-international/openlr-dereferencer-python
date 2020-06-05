"""Scoring functions and default weights for candidate line rating

FOW_WEIGHT + FRC_WEIGHT + GEO_WEIGHT + BEAR_WEIGHT should always be `1`.

The result of the scoring functions will be floats from 0.0 to 1.0,
with `1.0` being an exact match and 0.0 being a non-match."""

from math import degrees
from logging import debug
from openlr import FRC, FOW, LocationReferencePoint
from ..maps.wgs84 import project_along_path, distance, bearing
from .tools import coords, PointOnLine, linestring_coords
from .configuration import Config


def score_frc(wanted: FRC, actual: FRC) -> float:
    "Return a score for a FRC value"
    return 1.0 - abs(actual - wanted) / 7


def score_geolocation(
    wanted: LocationReferencePoint, actual: PointOnLine, radius: float, is_last_lrp: bool
) -> float:
    """Scores the geolocation of a candidate.

    A distance of `radius` or more will result in a 0.0 score."""
    debug(f"Candidate coords are {actual.position()}")
    dist = distance(coords(wanted), actual.position())
    if dist < radius:
        return 1.0 - dist / radius
    return 0.0

def score_angle_difference(angle1: float, angle2: float) -> float:
    """Helper for `score_bearing` which scores the angle difference.

    Args:
        angle1, angle2: angles, in degrees.
    Returns:
        The similarity of angle1 and angle2, from 0.0 (180° difference) to 1.0 (0° difference)
    """
    difference = (abs(angle1 - angle2) + 180) % 360 - 180
    return 1 - abs(difference) / 180


def score_bearing(wanted: LocationReferencePoint, actual: PointOnLine, is_last_lrp: bool, bear_dist: float) -> float:
    """Scores the difference between expected and actual bearing angle.

    A difference of 0° will result in a 1.0 score, while 180° will cause a score of 0.0."""
    line1, line2 = actual.split()
    if is_last_lrp:
        if line1 is None:
            return 0.0
        coordinates = linestring_coords(line1)
        coordinates.reverse()
    else:
        if line2 is None:
            return 0.0
        coordinates = linestring_coords(line2)
    absolute_offset = actual.line.length * actual.relative_offset
    bearing_point = project_along_path(coordinates, absolute_offset + bear_dist)
    bear = degrees(bearing(actual.position(), bearing_point))
    return score_angle_difference(wanted.bear, bear)


def score_lrp_candidate(
    wanted: LocationReferencePoint,
    candidate: PointOnLine, config: Config, is_last_lrp: bool
) -> float:
    """Scores the candidate (line) for the LRP.

    This is the average of fow, frc, geo and bearing score."""
    debug(f"scoring {candidate} with config {config}")
    score = (
        config.fow_weight * config.fow_standin_score[wanted.fow][candidate.line.fow]
        + config.frc_weight * score_frc(wanted.frc, candidate.line.frc)
        + config.geo_weight * score_geolocation(wanted, candidate, config.search_radius, is_last_lrp)
        + config.bear_weight * score_bearing(wanted, candidate, is_last_lrp, config.bear_dist)
    )
    debug(f"geo score: {score_geolocation(wanted, candidate, config.search_radius, is_last_lrp)}")
    debug(f"fow score: {config.fow_standin_score[wanted.fow][candidate.line.fow]}")
    debug(f"frc score: {score_frc(wanted.frc, candidate.line.frc)}")
    debug(f"bearing score: {score_bearing(wanted, candidate, is_last_lrp, config.bear_dist)}")
    debug(f"total score: {score}")
    return score
