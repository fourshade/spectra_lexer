import json

from .board import StenoBoardDefinitions
from .keys import StenoKeyLayout
from .rules import StenoRuleParser


class ResourceIO:
    """ Top-level IO for static steno resources. """

    def __init__(self, *, comment_prefix="#", encoding='utf-8') -> None:
        self._comment_prefix = comment_prefix  # Prefix for comments allowed in non-standard JSON files.
        self._encoding = encoding              # Encoding for text files. UTF-8 is explicitly required for some strings.

    def _cson_decode(self, s:str) -> dict:
        """ Decode a non-standard JSON string with full-line comments (CSON = commented JSON).
            JSON doesn't care about leading or trailing whitespace, so strip every line first. """
        lines = s.split("\n")
        stripped_line_iter = map(str.strip, lines)
        data_lines = [line for line in stripped_line_iter
                      if line and not line.startswith(self._comment_prefix)]
        s = "\n".join(data_lines)
        return json.loads(s)

    def _cson_load_dict(self, filename:str) -> dict:
        """ Load a string dict from a non-standard JSON file. """
        with open(filename, 'r', encoding=self._encoding) as fp:
            s = fp.read()
        return self._cson_decode(s)

    def load_keymap(self, filename:str) -> StenoKeyLayout:
        """ Load steno key layout constants from CSON. """
        d = self._cson_load_dict(filename)
        return StenoKeyLayout.from_json_dict(d)

    def load_rule_parser(self, filename:str) -> StenoRuleParser:
        """ Load steno rules from CSON. """
        d = self._cson_load_dict(filename)
        parser = StenoRuleParser()
        parser.add_json_dict(d)
        return parser

    def load_board_defs(self, filename:str) -> StenoBoardDefinitions:
        """ Load steno board graphics definitions from CSON. """
        d = self._cson_load_dict(filename)
        return StenoBoardDefinitions.from_json_dict(d)
