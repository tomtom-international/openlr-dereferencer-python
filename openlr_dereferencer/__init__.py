#!/usr/bin/env python3
"""
OpenLR line decoder package.
"""

from .decoding import decode, Config, load_config, save_config, DEFAULT_CONFIG
from .observer import DecoderObserver, SimpleObserver

from ._version import (
    __title__,
    __description__,
    __url__,
    __version__,
    __author__,
    __author_email__,
    __license__,
)
