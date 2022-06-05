# openlr-dereferencer

[![License](https://img.shields.io/badge/License-Apache%202.0-green.svg)](LICENSE)
[![Coverage Status](https://img.shields.io/codecov/c/github/tomtom-international/openlr-dereferencer-python/master.svg)](https://codecov.io/github/tomtom-international/openlr-dereferencer-python?branch=master)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/openlr-dereferencer)](https://pypi.org/project/openlr-dereferencer)
[![PyPI](https://img.shields.io/pypi/v/openlr-dereferencer)](https://pypi.org/project/openlr-dereferencer)
[![Documentation](https://readthedocs.org/projects/openlr-dereferencer-python/badge/)](https://openlr-dereferencer-python.readthedocs.io)


This is a Python package for decoding OpenLR™ location references on target maps.

It implements [Chapter G – Decoder](https://www.openlr-association.com/fileadmin/user_upload/openlr-whitepaper_v1.5.pdf#page=97) in the OpenLR whitepaper, except "Step 1 – decode physical data".

Its purpose is to give insights into the map-matching process.

## Dependencies
- Python ≥ 3.6
- geographiclib (PyPi package)
- shapely (PyPi package)
- [openlr](https://github.com/tomtom-international/openlr-python) (PyPi package; implements the decoder's step 1 from the whitepaper)
- For unittests: SpatiaLite
## State
- [X] Decoding line locations
- [X] Decoding 'point along line' locations
- [X] Decoding 'POI with access point' locations
## Structure
This package is divided into the following submodules:
### maps
Contains an abstract map class, which you may want to implement for your target map.

`maps.wgs84` provides methods for reckoning with WGS84 coordinates.
### example_sqlite_map
Implements the abstract map class for the example map format used in the unittests and examples
### decoding
The actual logic for matching references onto a map.

This includes finding candidate lines and scoring them, and assembling a dereferenced location.

### observer
Contains the observer class, allowing you to hook onto certain events in the decoding process.

## Installation
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

### Configuration
The `decode` function takes in an optional [Config](https://openlr-dereferencer-python.readthedocs.io/en/latest/openlr_dereferencer.decoding.html#openlr_dereferencer.decoding.configuration.Config) object containing decoding settings.
With it, you may specify the decoder's behaviour:
```py
from openlr_dereferencer import decode, Config

my_config = Config(
    geo_weight = 0.66,
    frc_height = 0.17,
    fow_height = 0.17,
    bear_weight = 0.0
)

decode(reference, mapreader, config=my_config)
```

### Logging
`openlr-dereferencer` logs all mapmatching decisions using the standard library `logging` module.

Use it to turn on debugging:
```py
import logging

logging.basicConfig(level=logging.DEBUG)
```

### Observing
Via implementing the [Observer](https://openlr-dereferencer-python.readthedocs.io/en/latest/openlr_dereferencer.observer.html#openlr_dereferencer.observer.simple_observer.SimpleObserver) interface, you can hook onto certain events happening while decoding, and inspect the situation:
```py
from openlr_dereferencer import DecoderObserver, SimpleObserver

# Look at SimpleObserver for an example implementation
my_observer = SimpleObserver()
decode(reference, mapreader, observer=my_observer)
```

## Development environment

Firstly create a Python virtual environment for the project.
```sh
python3 -m venv .venv
```

Activate the virtual environment.
```sh
source .venv/bin/activate
```

Install the dependency packages into the virtual environment.
```sh
pip install openlr geographiclib shapely

```

You may need to install the spatialite module for sqlite if this is not already present.
```sh
sudo apt install libsqlite3-mod-spatialite
```

To run the decoding tests.
```sh
python3 -m unittest
```

## More Documentation
You are welcomed to read the generated API documentation at https://openlr-dereferencer-python.readthedocs.io.
