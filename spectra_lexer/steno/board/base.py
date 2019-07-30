""" Module for generating steno board diagram elements and descriptions. """

from collections import defaultdict
from functools import lru_cache
from typing import Callable

from .elements import BoardElementProcessor, BoardFactory
from .matcher import KeyElementFinder, RuleElementFinder
from spectra_lexer.resource import KeyLayout, RulesDictionary, StenoRule, XMLElement


class BoardElementParser:
    """ Parser and catalog of SVG board elements by tag name. """

    _process: Callable          # Processes raw XML element nodes into full SVG board elements.
    _elems_by_tag: defaultdict  # Contains only elements with IDs, grouped into subdicts by tag.

    def __init__(self, root:XMLElement, processor:Callable):
        """ Parse the board XML into individual steno key/rule elements. """
        self._process = processor
        self._elems_by_tag = defaultdict(dict)
        self.add_recursive(root)

    def add_recursive(self, elem:XMLElement) -> None:
        """ Search for and process elements with IDs recursively. Make each child inherit from its predecessor. """
        e_id = elem.get("id")
        if e_id is not None:
            board_elem = self._process(elem)
            self._elems_by_tag[elem.tag][e_id] = board_elem
        else:
            for child in elem:
                child.update(elem, **child)
                self.add_recursive(child)

    def key_elems(self) -> list:
        return [self._elems_by_tag[k] for k in ("key", "qkey")]

    def rule_elems(self) -> dict:
        return self._elems_by_tag["rule"]

    def base_elems(self) -> list:
        return list(self._elems_by_tag["base"].values())


class BoardGenerator:
    """ Creates graphics for the board diagram. """

    _DEFAULT_RATIO: float = 100.0  # If no aspect ratio is given, this ensures that all boards end up in one row.

    _key_finder: KeyElementFinder
    _rule_finder: RuleElementFinder
    _build_document: BoardFactory

    def __init__(self, layout:KeyLayout, rules:RulesDictionary, board_defs:dict, board_elems:XMLElement):
        processor = BoardElementProcessor(board_defs)
        parser = BoardElementParser(board_elems, processor)
        kfinders = [KeyElementFinder(elems, layout.from_rtfcre, layout.SEP) for elems in parser.key_elems()]
        self._key_finder, _ = kfinders
        self._rule_finder = RuleElementFinder(parser.rule_elems(), rules, *kfinders)
        self._build_document = BoardFactory(parser.base_elems(), board_defs["bounds"])

    @lru_cache(maxsize=256)
    def from_keys(self, keys:str, aspect_ratio:float=_DEFAULT_RATIO) -> bytes:
        """ Generate a board diagram from keys. This isn't cheap, so the most recent ones are cached. """
        elems = self._key_finder(keys)
        return self._build_document(elems, aspect_ratio)

    @lru_cache(maxsize=256)
    def from_rule(self, rule:StenoRule, aspect_ratio:float=_DEFAULT_RATIO) -> bytes:
        """ Generate a board diagram from a rule. This isn't cheap, so the most recent ones are cached. """
        elems = self._rule_finder(rule)
        return self._build_document(elems, aspect_ratio)
