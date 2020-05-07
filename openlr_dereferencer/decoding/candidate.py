from typing import  NamedTuple
from ..maps import Line


class Candidate(NamedTuple):
    line: Line
    score: float
