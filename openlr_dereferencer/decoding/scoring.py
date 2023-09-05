"""Scoring functions and default weights for candidate line rating

FOW_WEIGHT + FRC_WEIGHT + GEO_WEIGHT + BEAR_WEIGHT should always be `1`.

The result of the scoring functions will be floats from 0.0 to 1.0,
with `1.0` being an exact match and 0.0 being a non-match."""

from logging import debug
from openlr import FRC, FOW, LocationReferencePoint
from ..maps.wgs84 import distance as distance_wgs84
from ..maps.equal_area import distance as distance_ee
from .path_math import coords, PointOnLine, compute_bearing
from .configuration import Config


def score_frc(wanted: FRC, actual: FRC) -> float:
    "Return a score for a FRC value"
    return 1.0 - abs(actual - wanted) / 7


def score_geolocation(wanted: LocationReferencePoint, actual: PointOnLine, radius: float, equal_area: bool) -> float:
    """Scores the geolocation of a candidate.

    A distance of `radius` or more will result in a 0.0 score."""
    debug(f"Candidate coords are {actual.position()}")
    if not equal_area:
        dist = distance_wgs84(coords(wanted), actual.position())
    else:
        dist = distance_ee(coords(wanted), actual.position())
    if dist < radius:
        return 1.0 - dist / radius
    return 0.0


def angle_sector(angle: float) -> int:
    """The bearing angles are mapped to one of  32 sectors, each of size 11.5°
    returns the sector the angle belongs to.

    Args:
        angle:
            the value is expected in degrees
    Returns:
        the sector to which the angle belongs to. Value in range [0,31]
    """

    if angle < 0:
        angle = angle + 360
    return int(angle / (360 / 32)) % 32


def angle_sector_difference(angle1: float, angle2: float) -> int:
    """ "The distance of the two sectors containing the angles values, respectively
    Args:
        angle1, angle2:
            the values are expected in degrees
    Returns:
        Value in the range [0,16]
    """

    sector_diff = abs(angle_sector(angle1) - angle_sector(angle2))
    "Differences should be between 0 and 16. Direction (clockwise or counter clockwise) between the two sectors should "
    "not matter. Thus map a difference (sector_diff) larger than 16 needs to be mapped to 32-sector_diff"
    if sector_diff > 16:
        sector_diff = 32 - sector_diff
    return sector_diff


def score_angle_sector_differences(angle1: float, angle2: float) -> float:
    """Helper for 'score_bearing which scores the angle difference

    Args:
        angle1, angle2:
            The values are expected in degrees.
    Returns:
        The similarity of the sectors of the angles, from 1.0 (same sector) to 0.0 (16 sectors difference)
    """

    sector_diff = angle_sector_difference(angle1, angle2)
    return 1.0 - (sector_diff / 16)


def angle_difference(angle1: float, angle2: float) -> float:
    """The difference of two angle values.

    Args:
        angle1, angle2:
            The values are expected in degrees.
    Returns:
        Value in the range [-180.0, 180.0]"""
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
    wanted: LocationReferencePoint, actual: PointOnLine, is_last_lrp: bool, bear_dist: float, equal_area: bool
) -> float:
    """Scores the difference between expected and actual bearing angle.

    A difference of 0° will result in a 1.0 score, while 180° will cause a score of 0.0."""
    bear = compute_bearing(wanted, actual, is_last_lrp, bear_dist, equal_area)
    return score_angle_sector_differences(wanted.bear, bear)


def score_lrp_candidate(
    wanted: LocationReferencePoint, candidate: PointOnLine, config: Config, is_last_lrp: bool
) -> float:
    """Scores the candidate (line) for the LRP.

    This is the average of fow, frc, geo and bearing score."""
    debug(f"scoring {candidate} with config {config}")
    geo_score = config.geo_weight * score_geolocation(wanted, candidate, config.search_radius, config.equal_area)
    fow_score = config.fow_weight * config.fow_standin_score[wanted.fow][candidate.line.fow]
    frc_score = config.frc_weight * score_frc(wanted.frc, candidate.line.frc)
    bear_score = score_bearing(wanted, candidate, is_last_lrp, config.bear_dist, config.equal_area)
    bear_score *= config.bear_weight
    score = fow_score + frc_score + geo_score + bear_score
    debug(f"Score: geo {geo_score} + fow {fow_score} + frc {frc_score} " f"+ bear {bear_score} = {score}")
    return score
