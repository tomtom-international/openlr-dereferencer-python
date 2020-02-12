# openlr_dereferencer
This is a Python package for decoding OpenLR™ location references on target maps.
## Dependencies
- Python ≥ 3.6
- geographiclib (PyPi package)
- openlr (PyPi package)
- For unittests, SQlite with spatialite extension is required
## State
- ☑ Example map format
- ☑ Routing
- ☑ Candidate route rating
- ☑ Backtracking to get correct routes
- ☑ Decoding line locations
- ☐ Decoding 'point along line' locations
- ☐ Decoding 'POI with access point' locations
## Structure
It is divided into the following submodules:
### maps
Contains an abstract map class, which you may want to implement for your target map.

`maps.wgs84` provides methods for reckoning with WGS84 coordinates.
### example_sqlite_map
Implements the abstract map class for the example map format used in the unittests and examples
### decoding
The actual logic for matching references onto a map.

This includes finding candidate lines and scoring them, and assembling a dereferenced location.


## Usage
The `decode(reference, mapreader)` function will take a location reference and return map objects.

### Usage Example

First, implement the `MapReader` class for your map.  The `example_sqlite_map` module is an implementation you may look at.

Second, construct a location reference. For instance, parse an OpenLR line location string:
```py
from openlr import binary_decode
reference = binary_decode("CwmG8yVjzCq0Dfzr/gErRRs=")
```

Third, decode the reference on an instance of your map reader class:
```py
from openlr_dereferencer import decode
real_location = decode(reference, mapreader)

real_location.lines # <- A list of map objects
```

## Configuration
### Candidates
The configuration value `openlr_dereferencer.SEARCH_RADIUS` determines how far away from the LRP road candidates are searched.
The unit is meters, the default 100.
### Scores
Every candidate line gets a score from `0` (bad) to `1` (perfect).

There are four scoring weight parameters:
 - GEO_WEIGHT = 0.25
 - FRC_WEIGHT = 0.25
 - FOW_WEIGHT = 0.25
 - BEAR_WEIGHT = 0.25

They determine how much influence a single aspect has on an overall candidate's score.
 
You may just change them before decoding:
```py
from openlr_dereferencer.decoding import scoring

scoring.GEO_WEIGHT = 0.66
scoring.FRC_WEIGHT = 0.17
scoring.FOW_WEIGHT = 0.17
scoring.BEAR_WEIGHT = 0
```
### Logging
`openlr-dereferencer` logs all mapmatching decisions using the standard library `logging` module.

Use it to turn on debugging:
```py
import logging

logging.basicConfig(level=logging.DEBUG)
```
