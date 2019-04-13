import os
from typing import Dict, Iterable, NamedTuple

from .rules import RuleParser
from spectra_lexer import Component
from spectra_lexer.file import CFG, CSON, SVG
from spectra_lexer.steno.keys import KeyLayout
from spectra_lexer.steno.rules import StenoRule


class StenoSystem(NamedTuple):
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
        """ Load the master config file for the system. Use default settings if missing. """
        main_cfg = filename or self.file
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
        return SVG.load(self.BOARD, ignore_missing=True) or {"raw": b"", "id": {}}

    @on("rules_save")
    def save_rules(self, rules:Iterable[StenoRule], filename:str="") -> None:
        """ From a bare iterable of rules (generally from the lexer), make a new raw dict and save it to JSON. """
        CSON.save(filename or self.out, self._rule_parser.inv_parse(rules), sort_keys=True)
