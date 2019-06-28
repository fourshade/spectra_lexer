""" Module for generating steno board diagram elements and descriptions. """

from collections import defaultdict
from functools import lru_cache

from .elements import BoardElement, BoardFactory
from .matcher import KeyElementFinder, RuleElementFinder
from ..base import LX
from spectra_lexer.resource import StenoRule
from spectra_lexer.types.codec import XMLElement


class BoardElementParser:
    """ Parser and catalog of SVG board elements by tag name. """

    _proc_defs: defaultdict
    _elems_by_tag: defaultdict

    def __init__(self, defs:dict, *elems:XMLElement):
        self._proc_defs = defaultdict(dict, defs)
        self._elems_by_tag = defaultdict(dict)
        for e in elems:
            self.add_recursive(e)

    def add_recursive(self, elem:XMLElement) -> None:
        """ Search for and process elements with IDs recursively. Make each child inherit from its predecessor. """
        e_id = elem.get("id")
        if e_id is not None:
            board_elem = self.parse(elem)
            self._elems_by_tag[elem.tag][e_id] = board_elem
        else:
            for child in elem:
                child.update(elem, **child)
                self.add_recursive(child)

    def parse(self, elem:XMLElement) -> BoardElement:
        board_elem = BoardElement(*map(self.parse, elem), **elem)
        board_elem.process(self._proc_defs)
        return board_elem

    def make_key_finders(self, *args) -> list:
        return [KeyElementFinder(self._elems_by_tag[k], *args) for k in ("key", "qkey")]

    def make_rule_finder(self, *args) -> RuleElementFinder:
        return RuleElementFinder(self._elems_by_tag["rule"], *args)

    def make_factory(self) -> BoardFactory:
        return BoardFactory(self._elems_by_tag["base"].values(), self._proc_defs["bounds"])


class BoardRenderer(LX):
    """ Creates graphics for the board diagram. """

    _DEFAULT_RATIO: float = 100.0  # If no aspect ratio is given, this ensures that all boards end up in one row.

    _key_finder: KeyElementFinder = None
    _rule_finder: RuleElementFinder = None
    _build_document: BoardFactory = None

    def Load(self) -> None:
        """ Parse the board XML into individual steno key/rule elements.
            Create sentinel elements for the stroke delimiter and stroke chain. """
        parser = BoardElementParser(self.BOARD_DEFS, self.BOARD_ELEMS)
        layout = self.LAYOUT
        kfinders = parser.make_key_finders(layout.from_rtfcre, layout.SEP)
        self._key_finder, _ = kfinders
        self._rule_finder = parser.make_rule_finder(self.RULES, *kfinders)
        self._build_document = parser.make_factory()

    @lru_cache(maxsize=256)
    def LXBoardFromKeys(self, keys:str, aspect_ratio:float=_DEFAULT_RATIO) -> bytes:
        """ Generate a board diagram from keys. This isn't cheap, so the most recent ones are cached. """
        elems = self._key_finder(keys)
        return self._build_document(elems, aspect_ratio)

    @lru_cache(maxsize=256)
    def LXBoardFromRule(self, rule:StenoRule, aspect_ratio:float=_DEFAULT_RATIO) -> bytes:
        """ Generate a board diagram from a rule. This isn't cheap, so the most recent ones are cached. """
        elems = self._rule_finder(rule)
        return self._build_document(elems, aspect_ratio)
