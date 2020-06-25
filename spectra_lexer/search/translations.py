""" Defines data types and provides I/O functions for JSON-compatible steno translations. """

import json
from typing import Dict, List, Tuple

Translation = Tuple[str, str]                   # A steno translation as a pair of strings: (RTFCRE keys, letters).
TranslationsDict = Dict[str, str]               # Dictionary mapping RTFCRE keys to letters.
RuleID = str                                    # Rule ID data type. Must be a string to act as a JSON object key.
ExamplesDict = Dict[RuleID, List[Translation]]  # Dictionary mapping rule identifiers to lists of example translations.


class TextFileIO:

    def __init__(self, *, encoding='utf-8') -> None:
        self._encoding = encoding  # Character encoding. UTF-8 must be explicitly set on some platforms.

    def read(self, filename:str) -> str:
        """ Load a text file into a string. """
        with open(filename, 'r', encoding=self._encoding) as fp:
            return fp.read()

    def write(self, filename:str, s:str) -> None:
        """ Save a string into a text file. """
        with open(filename, 'w', encoding=self._encoding) as fp:
            fp.write(s)


class TranslationsIO:

    def __init__(self) -> None:
        self._io = TextFileIO()  # IO for text files. UTF-8 is required for some translations.

    def load_json_translations(self, *filenames:str) -> TranslationsDict:
        """ Load and merge RTFCRE steno translations from JSON files. """
        translations = {}
        for filename in filenames:
            s = self._io.read(filename)
            try:
                d = json.loads(s)
                translations.update(d)
            except Exception as e:
                raise ValueError(f'Steno translations file "{filename}" is not formatted correctly.') from e
        return translations

    def load_json_examples(self, filename:str) -> ExamplesDict:
        """ Load an examples index from a JSON file formatted as a dict of dicts. """
        s = self._io.read(filename)
        try:
            obj_pairs = json.loads(s, object_pairs_hook=lambda x: x)
            assert {type(v) for _, v in obj_pairs} == {list}
        except Exception as e:
            raise ValueError(f'Examples index file "{filename}" is not formatted correctly.') from e
        return dict(obj_pairs)

    def save_json_examples(self, filename:str, examples:ExamplesDict) -> None:
        """ Save an examples index as a dict of dicts in JSON. Key sorting helps some algorithms run faster.
            ensure_ascii=False is required to preserve Unicode symbols. """
        d = {r_id: dict(translations) for r_id, translations in examples.items()}
        s = json.dumps(d, sort_keys=True, ensure_ascii=False)
        self._io.write(filename, s)
