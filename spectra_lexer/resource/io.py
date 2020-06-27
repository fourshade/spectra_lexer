from functools import wraps
import json
from typing import Any, Callable

from .board import StenoBoardDefinitions
from .keys import StenoKeyLayout
from .rules import StenoRuleList, StenoRuleParser
from .translations import ExamplesDict, TranslationsDict


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


class ResourceIOError(Exception):
    """ General exception for any resource IO or decoding error. """


def try_load(func:Callable) -> Callable:
    """ Decorator to re-raise I/O and parsing exceptions with more general error messages for the end-user. """
    @wraps(func)
    def load(self, filename:str) -> Any:
        try:
            return func(self, filename)
        except OSError as e:
            raise ResourceIOError(filename + ' is inaccessible or missing.') from e
        except (TypeError, ValueError) as e:
            raise ResourceIOError(filename + ' is not formatted correctly.') from e
        except Exception as e:
            raise ResourceIOError(filename + ' is incomplete or corrupt.') from e
    return load


class StenoResourceIO:
    """ Top-level IO for steno resources. """

    def __init__(self, io:TextFileIO=None, *, comment_prefix="#") -> None:
        self._io = io or TextFileIO()          # IO for text files.
        self._comment_prefix = comment_prefix  # Prefix for comments allowed in non-standard JSON files.

    def _cson_strip(self, s:str) -> str:
        """ Strip a non-standard JSON string of full-line comments (CSON = commented JSON).
            JSON doesn't care about leading or trailing whitespace, so strip every line first. """
        lines = s.split("\n")
        stripped_line_iter = map(str.strip, lines)
        data_lines = [line for line in stripped_line_iter
                      if line and not line.startswith(self._comment_prefix)]
        return "\n".join(data_lines)

    def _load_json_dict(self, filename:str) -> dict:
        """ Load a string dict from a UTF-8 JSON-based file. """
        s = self._io.read(filename)
        if filename.endswith(".cson"):
            s = self._cson_strip(s)
        d = json.loads(s)
        if not isinstance(d, dict):
            raise TypeError(filename + ' does not contain a string dictionary.')
        return d

    @try_load
    def load_keymap(self, filename:str) -> StenoKeyLayout:
        """ Load a steno key layout from CSON. """
        d = self._load_json_dict(filename)
        return StenoKeyLayout(**d)

    @try_load
    def load_rules(self, filename:str) -> StenoRuleList:
        """ Load steno rules from CSON. """
        d = self._load_json_dict(filename)
        parser = StenoRuleParser()
        for name, data in d.items():
            parser.add_json_data(name, data)
        return parser.parse()

    @try_load
    def load_board_defs(self, filename:str) -> StenoBoardDefinitions:
        """ Load steno board graphics definitions from CSON. """
        d = self._load_json_dict(filename)
        return StenoBoardDefinitions(**d)

    @try_load
    def _load_json_translations(self, filename:str) -> TranslationsDict:
        """ Load RTFCRE steno translations from a JSON file. """
        return self._load_json_dict(filename)

    def load_json_translations(self, *filenames:str) -> TranslationsDict:
        """ Load and merge RTFCRE steno translations from JSON files. """
        translations = {}
        for filename in filenames:
            d = self._load_json_translations(filename)
            translations.update(d)
        return translations

    @try_load
    def load_json_examples(self, filename:str) -> ExamplesDict:
        """ Load an examples index from a JSON file formatted as a dict of dicts. """
        examples = self._load_json_dict(filename)
        for v in examples.values():
            if not isinstance(v, dict):
                raise TypeError(filename + ' does not contain a nested string dictionary.')
        return examples

    def save_json_examples(self, filename:str, examples:ExamplesDict) -> None:
        """ Save an examples index as a dict of dicts in JSON. Key sorting helps some algorithms run faster.
            ensure_ascii=False is required to preserve Unicode symbols. """
        s = json.dumps(examples, sort_keys=True, ensure_ascii=False)
        self._io.write(filename, s)
