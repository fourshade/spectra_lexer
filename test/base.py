#!/usr/bin/env python3

""" Base test module for the Spectra steno lexer. Contains common resources. """

import json
import os

TRANSLATIONS_PATH = os.path.join(__file__, "..", "data", "translations.json")

with open(TRANSLATIONS_PATH) as fp:
    TEST_TRANSLATIONS = json.load(fp)
