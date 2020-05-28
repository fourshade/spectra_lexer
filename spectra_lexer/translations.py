import json
from typing import Dict

# Basic JSON translations data types.
TranslationsDict = Dict[str, str]
ExamplesDict = Dict[str, TranslationsDict]


class TranslationsIO:

    def __init__(self, *, encoding='utf-8') -> None:
        self._encoding = encoding  # Encoding for text files. UTF-8 is explicitly required for some strings.

    def _json_load_dict(self, filename:str) -> dict:
        """ Load a string dict from a JSON file. """
        with open(filename, 'r', encoding=self._encoding) as fp:
            return json.load(fp)

    def _json_dump_dict(self, filename:str, d:dict) -> None:
        """ Save a string dict to a JSON file. Key sorting helps some algorithms run faster.
            ensure_ascii=False is required to preserve Unicode symbols. """
        with open(filename, 'w', encoding=self._encoding) as fp:
            json.dump(d, fp, sort_keys=True, ensure_ascii=False)

    def load_json_translations(self, *filenames:str) -> TranslationsDict:
        """ Load and merge RTFCRE steno translations from JSON files. """
        translations = {}
        for filename in filenames:
            if filename.endswith(".json"):
                d = self._json_load_dict(filename)
                if not isinstance(d, dict):
                    raise TypeError(f'Steno translations file "{filename}" does not contain a dictionary.')
                translations.update(d)
        return translations

    def load_json_examples(self, filename:str) -> ExamplesDict:
        """ Load an examples index from a JSON file. """
        examples = self._json_load_dict(filename)
        if not isinstance(examples, dict) or not all([isinstance(v, dict) for v in examples.values()]):
            raise TypeError(f'Examples index file "{filename}" does not contain a dict of dicts.')
        return examples

    def save_json_examples(self, filename:str, examples:ExamplesDict) -> None:
        """ Save an examples index as a dict of dicts in JSON. """
        self._json_dump_dict(filename, examples)
