import os
from typing import Dict, Iterable

from .rules import RuleParser
from spectra_lexer import Component
from spectra_lexer.file import CFG, CSON, XML
from spectra_lexer.steno.keys import KeyLayout
from spectra_lexer.steno.rules import StenoRule
from spectra_lexer.struct import struct


class StenoSystem(struct, _fields=["layout", "rules", "rev_rules", "board"]):
    """ Description of a complete steno system, including key layout, rules, and (optional) board graphics. """

    layout: KeyLayout
    rules: Dict[str, StenoRule]
    rev_rules: Dict[StenoRule, str]
    board: dict


class SystemManager(Component):
    """ Component to load all assets necessary for a steno system and send them to other components as a group. """

    # Glob pattern for JSON-based rules files, relative to the master CFG.
    RULES = "*.cson"

    # File path for the SVG steno board graphics, relative to the master CFG.
    BOARD = "board.svg"

    file = resource("cmdline:system-cfg", ":/assets/default/master.cfg", desc="File with system resources")
    out = resource("cmdline:rules-out", "./rules.json", desc="Output file name for lexer-generated rules.")

    _rule_parser: RuleParser  # Parses steno rules in both directions.

    def __init__(self):
        super().__init__()
        self._rule_parser = RuleParser()

    @on("init:system", pipe_to="res:system:")
    def start(self, *dummy) -> StenoSystem:
        return self.load()

    @on("system_load", pipe_to="res:system:")
    def load(self, filename:str="") -> StenoSystem:
        """ Load the system master file in <filename>, then create the system with the key layout,
            both the forward and reverse rules dicts, and the SVG board layout (optional). """
        keys = self.load_master(filename or self.file)
        rules, rev_rules = self.load_rules()
        board = self.load_board()
        return StenoSystem(keys, rules, rev_rules, board)

    def load_master(self, main_cfg:str) -> KeyLayout:
        """ Load the master config file for the system. Use default settings if missing. """
        folder, _ = os.path.split(main_cfg)
        cfg = CFG.load(main_cfg, ignore_missing=True)
        files = cfg.get("files")
        if files:
            f = {k.upper(): os.path.join(folder, v) for k, v in files.items()}
            self.__dict__.update(f)
        layout = cfg.get("keys")
        if layout:
            return KeyLayout({k.upper: v for k, v in layout.items()})
        return KeyLayout({})

    def load_rules(self) -> tuple:
        """ Load all rules for the system. This operation must not fail. """
        dicts = CSON.load_all(self.RULES)
        rules = self._rule_parser.parse(dicts)
        return rules, self._rule_parser.invert(rules)

    def load_board(self) -> dict:
        """ Load an SVG file and keep the raw XML data along with all element IDs.
            The board is not necessary to run the lexer; return empty fields if it can't be loaded. """
        return XML.load(self.BOARD, ignore_missing=True) or XML.decode(b"")

    @on("rules_save")
    def save_rules(self, rules:Iterable[StenoRule], filename:str="") -> None:
        """ From a bare iterable of rules (generally from the lexer), make a new raw dict and save it to JSON. """
        CSON.save(filename or self.out, self._rule_parser.inv_parse(rules), sort_keys=True)
