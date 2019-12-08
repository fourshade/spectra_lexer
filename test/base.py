#!/usr/bin/env python3

""" Base test module for the Spectra steno lexer. Contains common resources and pre-built objects. """

import json
import os

from spectra_lexer.base import Spectra, StenoEngineFactory

TRANSLATIONS_PATH = os.path.join(__file__, "..", "data", "translations.json")

# Create all test resources using default assets.
MAIN = Spectra()
KEY_LAYOUT = MAIN.load_keymap()
RULES = MAIN.load_rules()
RULES_DICT = {rule.id: (rule.keys, rule.letters) for rule in RULES}
BOARD_DEFS = MAIN.load_board_defs()
FACTORY = StenoEngineFactory(KEY_LAYOUT, RULES, BOARD_DEFS)
with open(TRANSLATIONS_PATH) as fp:
    TEST_TRANSLATIONS = json.load(fp)
