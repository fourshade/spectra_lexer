import os
from typing import Dict, Iterable

from spectra_lexer import Component
from spectra_lexer.file import CFG, CSON, XML
from spectra_lexer.steno.rules import StenoRule
from spectra_lexer.steno.system.keys import KeyLayout
from spectra_lexer.steno.system.rules import RuleParser
from spectra_lexer.utils import delegate_to


class StenoSystem:

    keys: KeyLayout
    rules: Dict[str, StenoRule]
    rev_rules: Dict[StenoRule, str]
    board: dict

    def __init__(self, keys:KeyLayout, rules:Dict[str,StenoRule], rev_rules:Dict[StenoRule,str], board:dict):
        self.keys = keys
        self.rules = rules
        self.rev_rules = rev_rules
        self.board = board

    to_rtfcre = delegate_to("keys")
    from_rtfcre = delegate_to("keys")
    cleanse_from_rtfcre = delegate_to("keys")


class SystemManager(Component):

    # Glob pattern for JSON-based rules files, relative to the master CFG.
    RULES = "*.cson"

    # File path for the SVG steno board graphics, relative to the master CFG.
    BOARD = "board.svg"

    file = Resource("cmdline", "system-cfg", ":/assets/default/master.cfg", "File with system resources")
    out = Resource("cmdline", "rules-out", "./rules.json", "Output file name for lexer-generated rules.")

    _rule_parser: RuleParser  # Parses steno rules in both directions.

    def __init__(self):
        super().__init__()
        self._rule_parser = RuleParser()

    @on("load_dicts", pipe_to="set_system")
    @on("system_load", pipe_to="set_system")
    def load_system(self, filename:str="") -> StenoSystem:
        """ Load the system master file in <filename>, then create the system with the key layout,
            both the forward and reverse rules dicts, and the SVG board layout (optional). """
        keys = self.load(filename)
        rules, rev_rules = self.load_rules()
        board = self.load_board()
        return StenoSystem(keys, rules, rev_rules, board)

    def load(self, filename:str="") -> KeyLayout:
        main_cfg = filename or self.file
        folder, _ = os.path.split(main_cfg)
        try:
            cfg = CFG.load(main_cfg)
        except OSError:
            return KeyLayout({})
        files = cfg.get("files")
        if files:
            f = {k.upper(): os.path.join(folder, v) for k, v in files.items()}
            self.__dict__.update(f)
        keys = cfg.get("keys")
        if keys:
            return KeyLayout({k.upper: v for k, v in keys.items()})
        return KeyLayout({})

    def load_rules(self) -> tuple:
        dicts = CSON.load_all(self.RULES)
        rules = self._rule_parser.parse(dicts)
        return rules, self._rule_parser.invert(rules)

    def load_board(self) -> dict:
        """ Load an SVG file and keep the raw SVG text data along with all element IDs.
            The board is not necessary to run the lexer; skip it if can't be loaded. """
        try:
            return XML.load(self.BOARD)
        except OSError:
            return {"raw": "", "ids": {}}

    @on("rules_save")
    def save_rules(self, rules:Iterable[StenoRule], filename:str= "") -> None:
        """ From a bare iterable of rules (generally from the lexer), make a new raw dict and save it to JSON. """
        CSON.save(filename or self.out, self._rule_parser.inv_parse(rules))
