""" Module for generating steno board diagram elements and descriptions. """

from collections import defaultdict
from typing import Dict, Tuple

from .elements import BoardElementProcessor, BoardFactory
from .matcher import KeyElementFinder, RuleElementFinder
from .xml import XMLElement
from ..keys import KeyLayout
from ..rules import StenoRule


class BoardElementParser:
    """ Parser and catalog of SVG board elements by tag name. """

    _process: BoardElementProcessor  # Processes raw XML element nodes into full SVG board elements.
    _elems_by_tag: defaultdict       # Contains only elements with IDs, grouped into subdicts by tag.

    def __init__(self,  board_defs:dict, xml_data:bytes) -> None:
        """ Parse the board XML into individual steno key/rule elements. """
        self._process = BoardElementProcessor(board_defs)
        self._elems_by_tag = defaultdict(dict)
        root = XMLElement.decode(xml_data)
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

    def key_elems(self) -> Tuple[dict, dict]:
        """ Return the element dicts corresponding to known and unknown keys, respectively. """
        d = self._elems_by_tag
        return d["key"], d["qkey"]

    def rule_elems(self) -> dict:
        """ Return the element dict corresponding to known rule identifiers. """
        return self._elems_by_tag["rule"]

    def base_elems(self) -> list:
        """ Return the list of elements that make up the base present in every stroke. """
        return list(self._elems_by_tag["base"].values())


class BoardGenerator:
    """ Creates graphics for the board diagram. """

    _DEFAULT_RATIO: float = 100.0  # If no aspect ratio is given, this ensures that all boards end up in one row.

    _key_finder: KeyElementFinder
    _rule_finder: RuleElementFinder
    _build_document: BoardFactory

    def __init__(self, layout:KeyLayout, rules:Dict[str, StenoRule], board_defs:dict, board_xml:bytes) -> None:
        parser = BoardElementParser(board_defs, board_xml)
        kfinder, ukfinder = [KeyElementFinder(elems, layout.from_rtfcre, layout.SEP) for elems in parser.key_elems()]
        self._key_finder = kfinder
        self._rule_finder = RuleElementFinder(parser.rule_elems(), rules, kfinder, ukfinder)
        self._build_document = BoardFactory(parser.base_elems(), board_defs["bounds"])

    def from_keys(self, keys:str, aspect_ratio:float=_DEFAULT_RATIO) -> bytes:
        """ Generate encoded board diagram layouts arranged according to <aspect_ratio> from a set of steno keys. """
        elems = self._key_finder(keys)
        return self._build_document(elems, aspect_ratio)

    def from_rule(self, rule:StenoRule, aspect_ratio:float=_DEFAULT_RATIO) -> bytes:
        """ Generate encoded board diagram layouts arranged according to <aspect_ratio> from a steno rule. """
        elems = self._rule_finder(rule)
        return self._build_document(elems, aspect_ratio)
