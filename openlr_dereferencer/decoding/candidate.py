from typing import Optional
from .routes import PointOnLine

class Candidate(PointOnLine):
    "An LRP candidate, represented by a point on the road network along with its score"
    score: Optional[float] = None
    "The candidate may be bundled together with it's precomputed score."