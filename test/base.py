#!/usr/bin/env python3

""" Base test module for the Spectra steno lexer. Contains common resources and pre-built objects. """

import json
import os

from spectra_lexer.base import StenoAppFactory


def _test_json_read(filename:str) -> dict:
    """ Read from JSON test data (e.g. translations that should all have matches). """
    path = os.path.join(__file__, "..", "data", filename)
    with open(path) as fp:
        return json.load(fp)


# Create all test resources using default command-line arguments.
TEST_TRANSLATIONS = _test_json_read("translations.json")
TEST_INDEX = _test_json_read("index.json")
MAIN = StenoAppFactory()
KEY_LAYOUT = MAIN.load_layout()
RULES = list(MAIN.load_rules())
RULES_DICT = {rule.name: (rule.keys, rule.letters) for rule in RULES}
IGNORED_KEYS = {KEY_LAYOUT.sep, KEY_LAYOUT.split}
FACTORY = MAIN.build_factory()
