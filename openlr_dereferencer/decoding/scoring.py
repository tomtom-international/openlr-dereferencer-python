"""Scoring functions and default weights for candidate line rating

FOW_WEIGHT + FRC_WEIGHT + GEO_WEIGHT + BEAR_WEIGHT should always be `1`.

The result of the scoring functions will be floats from 0.0 to 1.0,
with `1.0` being an exact match and 0.0 being a non-match."""

from logging import debug
from openlr import FRC, FOW, LocationReferencePoint
from ..maps.wgs84 import distance
from .tools import coords, PointOnLine
from .configuration import Config
from .tools import compute_bearing


def score_frc(wanted: FRC, actual: FRC) -> float:
    "Return a score for a FRC value"
    return 1.0 - abs(actual - wanted) / 7


def score_geolocation(wanted: LocationReferencePoint, actual: PointOnLine, radius: float) -> float:
    """Scores the geolocation of a candidate.

    A distance of `radius` or more will result in a 0.0 score."""
    debug(f"Candidate coords are {actual.position()}")
    dist = distance(coords(wanted), actual.position())
    if dist < radius:
        return 1.0 - dist / radius
    return 0.0

def angle_difference(angle1: float, angle2: float) -> float:
    """The difference of two angle values.

    Args:
        angle1, angle2:
            The values are expected in degrees.
    Returns:
        A value in the range [-180.0, 180.0]"""
    return (abs(angle1 - angle2) + 180) % 360 - 180

def score_angle_difference(angle1: float, angle2: float) -> float:
    """Helper for `score_bearing` which scores the angle difference.

    Args:
        angle1, angle2: angles, in degrees.
    Returns:
        The similarity of angle1 and angle2, from 0.0 (180° difference) to 1.0 (0° difference)
    """
    difference = angle_difference(angle1, angle2)
    return 1 - abs(difference) / 180


def score_bearing(
        wanted: LocationReferencePoint,
        actual: PointOnLine,
        is_last_lrp: bool,
        bear_dist: float
) -> float:
    """Scores the difference between expected and actual bearing angle.

    A difference of 0° will result in a 1.0 score, while 180° will cause a score of 0.0."""
    bear = compute_bearing(wanted, actual, is_last_lrp, bear_dist)
    return score_angle_difference(wanted.bear, bear)


def score_lrp_candidate(
        wanted: LocationReferencePoint,
        candidate: PointOnLine, config: Config, is_last_lrp: bool
) -> float:
    """Scores the candidate (line) for the LRP.

    This is the average of fow, frc, geo and bearing score."""
    debug(f"scoring {candidate} with config {config}")
    geo_score = config.geo_weight * score_geolocation(wanted, candidate, config.search_radius)
    fow_score = config.fow_weight * config.fow_standin_score[wanted.fow][candidate.line.fow]
    frc_score = config.frc_weight * score_frc(wanted.frc, candidate.line.frc)
    bear_score = score_bearing(wanted, candidate, is_last_lrp, config.bear_dist)
    bear_score *= config.bear_weight
    score = fow_score + frc_score + geo_score + bear_score
    debug(f"Score: geo {geo_score} + fow {fow_score} + frc {frc_score} "
          f"+ bear {bear_score} = {score}")
    return score
