# openlr-dereferencer

[![License](https://img.shields.io/badge/License-Apache%202.0-green.svg)](LICENSE)
[![Build status](https://img.shields.io/travis/tomtom-international/openlr-dereferencer-python)](https://travis-ci.org/tomtom-international/openlr-dereferencer-python)
[![Coverage Status](https://img.shields.io/codecov/c/github/tomtom-international/openlr-dereferencer-python/master.svg)](https://codecov.io/github/tomtom-international/openlr-dereferencer-python?branch=master)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/openlr-dereferencer)](https://pypi.org/project/openlr-dereferencer)
[![PyPI](https://img.shields.io/pypi/v/openlr-dereferencer)](https://pypi.org/project/openlr-dereferencer)
[![Documentation](https://readthedocs.org/projects/openlr-dereferencer-python/badge/)](https://openlr-dereferencer-python.readthedocs.io)


This is a Python package for decoding OpenLR™ location references on target maps.
## Dependencies
- Python ≥ 3.6
- geographiclib (PyPi package)
- shapely (PyPi package)
- [openlr](https://github.com/tomtom-international/openlr-python) (PyPi package)
- For unittests, SQlite with spatialite extension is required
## State
- ☑ Decoding line locations
- ☑ Decoding 'point along line' locations
- ☑ Decoding 'POI with access point' locations
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

# Installation
This project is available on PyPi:
```sh
pip3 install openlr-dereferencer
```

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
 
You may just change these before decoding:
```py
from openlr_dereferencer.decoding import scoring

scoring.GEO_WEIGHT = 0.66
scoring.FRC_WEIGHT = 0.17
scoring.FOW_WEIGHT = 0.17
scoring.BEAR_WEIGHT = 0
```

A value of 0 means that the aspect has no influence on the candidate score, while a value of 1 means that it is the only aspect that matters.
### Logging
`openlr-dereferencer` logs all mapmatching decisions using the standard library `logging` module.

Use it to turn on debugging:
```py
import logging

logging.basicConfig(level=logging.DEBUG)
```

## More Documentation
You are welcomed to read the generated API documentation at https://openlr-dereferencer-python.readthedocs.io.