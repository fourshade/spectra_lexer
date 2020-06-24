import json
from typing import Dict

# Basic JSON translations data types.
TranslationsDict = Dict[str, str]
ExamplesDict = Dict[str, TranslationsDict]


class TextFileIO:

    def __init__(self, **kwargs) -> None:
        self._open_kwargs = kwargs  # Keyword arguments to open().

    def read(self, filename:str) -> str:
        """ Load a text file into a string. """
        with open(filename, 'r', **self._open_kwargs) as fp:
            return fp.read()

    def write(self, filename:str, s:str) -> None:
        """ Save a string into a text file. """
        with open(filename, 'w', **self._open_kwargs) as fp:
            fp.write(s)


class TranslationsIO:

    def __init__(self) -> None:
        self._io = TextFileIO(encoding='utf-8')  # IO for text files. UTF-8 is explicitly required for some strings.

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
        examples = json.loads(s)
        if not isinstance(examples, dict) or not all([isinstance(v, dict) for v in examples.values()]):
            raise TypeError(f'Examples index file "{filename}" does not contain a dict of dicts.')
        return examples

    def save_json_examples(self, filename:str, examples:ExamplesDict) -> None:
        """ Save an examples index as a dict of dicts in JSON. Key sorting helps some algorithms run faster.
            ensure_ascii=False is required to preserve Unicode symbols. """
        s = json.dumps(examples, sort_keys=True, ensure_ascii=False)
        self._io.write(filename, s)
