"Contains the configuration object that can be passed to the decoder, as well as default values"
from typing import NamedTuple, List, Dict, Union, Optional
from io import TextIOBase
from json import loads, dumps
from openlr import FRC, FOW

#: The default value for the `fow_standin_score` config option.
#: The values are adopted from the openlr Java implementation.
DEFAULT_FOW_STAND_IN_SCORE = [
    [0.50, 0.50, 0.50, 0.50, 0.50, 0.50, 0.50, 0.5],  # Undefined FOW
    [0.50, 1.00, 0.75, 0.00, 0.00, 0.00, 0.00, 0.0],  # Motorway
    [0.50, 0.75, 1.00, 0.75, 0.50, 0.00, 0.00, 0.0],  # Multiple carriage way
    [0.50, 0.00, 0.75, 1.00, 0.50, 0.50, 0.00, 0.0],  # Single carriage way
    [0.50, 0.00, 0.50, 0.50, 1.00, 0.50, 0.00, 0.0],  # Roundabout
    [0.50, 0.00, 0.00, 0.50, 0.50, 1.00, 0.00, 0.0],  # Traffic quare
    [0.50, 0.00, 0.00, 0.00, 0.00, 0.00, 1.00, 0.0],  # Sliproad
    [0.50, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 1.0],  # Other FOW
]

class Config(NamedTuple):
    """A config object that provides all settings that influences the decoder's behaviour
    
    Customize the values where the default won't fit you:

    .. code-block:: python

        myconfig = Config(min_score=0.9, search_radius=10)
    """

    #: Configures the default radius to search for map objects around an LRP. This value is in meters.
    search_radius: float = 100.0
    #: Tolerable relative DNP deviation of a path
    #:
    #: A path between consecutive LRPs may deviate from the DNP by this relative value plus
    #: :py:attr:`~tolerated_dnp_dev` in order to be considered. The value here is relative
    #: to the expected distance to next point.
    max_dnp_deviation: float = 0.3
    #: Additional buffer to the range of allowed path distance
    #:
    #: In order to be considered, a path must not deviate from the DNP value by more than
    #: :py:attr:`~max_dnp_deviation` (relative value) plus :py:attr:`~tolerated_dnp_dev`. This value is in meters.
    tolerated_dnp_dev: int = 30
    #: A filter for candidates with insufficient score. Candidates below this score are not considered.
    #: As this value is a score, it is in the range of [0.0, 1.0].
    min_score: float = 0.3
    #: For every LFRCNP possibly present in an LRP, this defines
    #: what lowest FRC in a considered route is acceptable
    tolerated_lfrc: Dict[FRC, FRC] = {frc:frc for frc in FRC}
    #: Partial candidate line threshold, measured in meters
    #:
    #: To find candidates, the LRP coordinates are projected against any line in the local area.
    #: If the distance from the starting point is greater than this threshold, the partial line
    #: beginning at the projection point is considered to be the candidate. Else, the candidate
    #: snaps onto the starting point (or ending point, when it is the last LRP)
    candidate_threshold: int = 20
    #: Defines the weight the FOW score has on the overall score of a candidate.
    fow_weight: float = 1 / 4
    #: Defines the weight the FRC score has on the overall score of a candidate.
    frc_weight: float = 1 / 4
    #: Defines the weight the coordinate difference has on the overall score of a candidate.
    geo_weight: float = 1 / 4
    #: Defines the weight the bearing score has on the overall score of a candidate.
    bear_weight: float = 1 / 4
    #: When comparing an LRP FOW with a candidate's FOW, this matrix defines
    #: how well the candidate's FOW fits as replacement for the expected value.
    #: The usage is `fow_standin_score[lrp's fow][candidate's fow]`.
    #: It returns the score.
    fow_standin_score: List[List[float]] = DEFAULT_FOW_STAND_IN_SCORE
    #: The bearing angle is computed along this distance on a given line. Given in meters.
    bear_dist: int = 20


DEFAULT_CONFIG = Config()

def load_config(source: Union[str, TextIOBase, dict]) -> Config:
    """Load config from a source
    
    Args:
        source:
            Either an open text file containing a JSON dict, or the path to it, or a dictionary
    Returns:
        The read Config object
    """
    file_open = None
    opened_source = source
    if isinstance(opened_source, str):
        opened_source = open(source, "r")
        file_open = opened_source
    if isinstance(opened_source, TextIOBase):
        opened_source = loads(opened_source.read())
    if file_open is not None:
        file_open.close()
    if not isinstance(opened_source, dict):
        raise TypeError("Surprising type")
    return Config._make(
        [
            opened_source['search_radius'],
            opened_source['max_dnp_deviation'],
            opened_source['tolerated_dnp_dev'],
            opened_source['min_score'],
            {
                FRC(int(key)): FRC(value)
                for (key, value) in opened_source['tolerated_lfrc'].items() 
            },
            opened_source['candidate_threshold'],
            opened_source['fow_weight'],
            opened_source['frc_weight'],
            opened_source['geo_weight'],
            opened_source['bear_weight'],
            opened_source['fow_standin_score'],
            opened_source['bear_dist']
        ]
    )


def save_config(config: Config, dest: Union[str, TextIOBase, type(None)] = None) -> Optional[dict]:
    """Saves a config to a file or a dictionary
    
    Args:
        dest:
            Either a path, or an already write-opened text file, or nothing.
    Returns:
        If no destination was given, returns the config as dictionary"""
    if dest is None:
        return config._asdict()
    if isinstance(dest, str):
        with open(dest, "w") as fp:
            save_config(config, fp)
    if isinstance(dest, TextIOBase):
        dest.write(dumps(save_config(config)))
