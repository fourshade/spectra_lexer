import os
from typing import Iterable

from .keys import KeyLayout
from .rules import RulesDictionary, StenoRule
from spectra_lexer.core import COREApp, Component, Resource
from spectra_lexer.system import CmdlineOption, ConsoleCommand, SYSFile
from spectra_lexer.types.codec import XMLElement


class BoardElementTree(XMLElement):
    pass


class LXSystem:

    @ConsoleCommand("system_load")
    def load(self, filename:str="") -> tuple:
        raise NotImplementedError

    @ConsoleCommand("rules_save")
    def save_rules(self, rules:Iterable[StenoRule], filename:str="") -> None:
        raise NotImplementedError

    class Layout:
        layout: KeyLayout = Resource()

    class Rules:
        rules: RulesDictionary = Resource()

    class Board:
        board: BoardElementTree = Resource()


class SystemManager(Component, LXSystem,
                    COREApp.Start):
    """ Component to load all assets necessary for a steno system and send them to other components as a group.
        Assets include a key layout, rules, and (optional) board graphics. """

    path = CmdlineOption("system-dir", default=":/assets/default/", desc="Directory with system resources")
    out = CmdlineOption("rules-out", default="./rules.json", desc="Output file name for lexer-generated rules.")

    LAYOUT_PATH = "layout.json"  # File name for the steno key constants in the base directory.
    RULES_PATH = "*.cson"        # Glob pattern for JSON-based rules files in the base directory.
    BOARD_PATH = "board.xml"     # File name for the XML steno board graphics in the base directory.

    _rules: RulesDictionary = RulesDictionary()  # Parses steno rules in both directions.

    def on_app_start(self) -> None:
        self.load()

    def load(self, base_path:str="") -> list:
        """ From files in in <base_path>, create the system with the key layout, rule dict, and board layout. """
        path = base_path or self.path
        return [load_fn(path) for load_fn in (self._load_layout, self._load_rules, self._load_board)]

    def _load_layout(self, base_dir:str) -> KeyLayout:
        """ Load the master config file for the system. Use default settings if missing. """
        path = os.path.join(base_dir, self.LAYOUT_PATH)
        layout = KeyLayout.decode(self.engine_call(SYSFile.read, path, ignore_missing=True))
        self.engine_call(self.Layout, layout)
        return layout

    def _load_board(self, base_dir:str) -> BoardElementTree:
        """ Load an SVG file and keep the raw XML data along with all element IDs.
            The board is not necessary to run the lexer; return empty fields if it can't be loaded. """
        path = os.path.join(base_dir, self.BOARD_PATH)
        board = BoardElementTree.decode(self.engine_call(SYSFile.read, path, ignore_missing=True))
        self.engine_call(self.Board, board)
        return board

    def _load_rules(self, base_dir:str) -> RulesDictionary:
        """ Load all rules for the system. This operation must not fail. """
        path = os.path.join(base_dir, self.RULES_PATH)
        rules = self._rules = RulesDictionary.decode(*self.engine_call(SYSFile.read_all, [path]))
        self.engine_call(self.Rules, rules)
        return rules

    def save_rules(self, rules:Iterable[StenoRule], filename:str="") -> None:
        """ From a bare iterable of rules (generally from the lexer), make a new raw dict and save it to JSON. """
        data = self._rules.encode_other(rules, sort_keys=True)
        self.engine_call(SYSFile.write, filename or self.out, data)
