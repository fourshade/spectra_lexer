#!/usr/bin/env python3

""" Base test module for the Spectra steno lexer. Contains common resources and pre-built objects. """

import os

from spectra_lexer.base import StenoMain
from spectra_lexer.io import ResourceIO


def _test_json_read(io:ResourceIO, filename:str) -> dict:
    """ Read from program test data (e.g. translations that should all have matches). """
    return io.json_read(os.path.join(__file__, "..", "data", filename))


# Create all test resources using default command-line arguments.
MAIN = StenoMain()
TEST_IO = MAIN.build_io()
TEST_TRANSLATIONS = _test_json_read(TEST_IO, "translations.json")
TEST_INDEX = _test_json_read(TEST_IO, "index.json")
KEY_LAYOUT = MAIN.load_layout(TEST_IO)
RULES = list(MAIN.load_rules(TEST_IO))
RULES_DICT = {rule.name: (rule.keys, rule.letters) for rule in RULES}
IGNORED_KEYS = {KEY_LAYOUT.sep, KEY_LAYOUT.split}
FACTORY = MAIN.build_factory(TEST_IO)
