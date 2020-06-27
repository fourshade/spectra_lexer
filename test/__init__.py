""" Test package for the Spectra steno lexer. __init__.py loads common test resources. """

import json
import os

_translations_path = os.path.join(__file__, "..", "data", "translations.json")
with open(_translations_path) as fp:
    TEST_TRANSLATIONS = json.load(fp)
del _translations_path
