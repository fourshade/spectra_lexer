from functools import wraps
import json
from typing import Any, Callable

from .board import StenoBoardDefinitions
from .keys import StenoKeyLayout
from .rules import StenoRuleList, StenoRuleParser


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
        except Exception as e:
            raise ResourceIOError(filename + ' is incomplete or corrupt.') from e
    return load


class ResourceIO:
    """ Top-level IO for static steno resources. """

    def __init__(self, *, comment_prefix="#") -> None:
        self._comment_prefix = comment_prefix  # Prefix for comments allowed in non-standard JSON files.

    def _cson_decode(self, s:str) -> Any:
        """ Decode a non-standard JSON string with full-line comments (CSON = commented JSON).
            JSON doesn't care about leading or trailing whitespace, so strip every line first. """
        lines = s.split("\n")
        stripped_line_iter = map(str.strip, lines)
        data_lines = [line for line in stripped_line_iter
                      if line and not line.startswith(self._comment_prefix)]
        s = "\n".join(data_lines)
        return json.loads(s)

    def _cson_load_dict(self, filename:str) -> dict:
        """ Load a string dict from a non-standard UTF-8 JSON file. """
        with open(filename, 'r', encoding='utf-8') as fp:
            s = fp.read()
        d = self._cson_decode(s)
        if not isinstance(d, dict):
            raise TypeError(filename + ' does not contain a string dictionary.')
        return d

    @try_load
    def load_keymap(self, filename:str) -> StenoKeyLayout:
        """ Load a steno key layout from CSON. """
        d = self._cson_load_dict(filename)
        return StenoKeyLayout(**d)

    @try_load
    def load_rules(self, filename:str) -> StenoRuleList:
        """ Load steno rules from CSON. """
        d = self._cson_load_dict(filename)
        parser = StenoRuleParser()
        for name, data in d.items():
            parser.add_json_data(name, data)
        return parser.parse()

    @try_load
    def load_board_defs(self, filename:str) -> StenoBoardDefinitions:
        """ Load steno board graphics definitions from CSON. """
        d = self._cson_load_dict(filename)
        return StenoBoardDefinitions(**d)
