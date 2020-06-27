""" Defines data types for JSON-compatible steno translations. """

from typing import Dict, Tuple

Translation = Tuple[str, str]                  # A steno translation as a pair of strings: (RTFCRE keys, letters).
TranslationsDict = Dict[str, str]              # Dictionary mapping RTFCRE keys to letters.
RuleID = str                                   # Rule ID data type. Must be a string to act as a JSON object key.
ExamplesDict = Dict[RuleID, TranslationsDict]  # Dictionary mapping rule identifiers to example translation dicts.
