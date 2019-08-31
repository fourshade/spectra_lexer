""" Module for generating steno board diagram elements and descriptions. """

from collections import defaultdict
from typing import Dict

from .elements import BoardElementProcessor, BoardFactory, BoardElement
from .matcher import KeyElementFinder, ElementFinder
from .xml import XMLElement
from ..keys import KeyLayout
from ..rules import StenoRule


class BoardElementParser:
    """ Parser and catalog of SVG board elements by tag name. """

    def __init__(self, processor:BoardElementProcessor) -> None:
        """ Parse the board XML into individual steno key/rule elements. """
        self._process = processor               # Processes raw XML element nodes into full SVG board elements.
        self._elems_by_tag = defaultdict(dict)  # Contains only elements with IDs, grouped into subdicts by tag.

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

    def key_elems(self) -> dict:
        """ Return the element dicts corresponding to single steno keys. """
        return self._elems_by_tag["key"]

    def unmatched_elems(self) -> dict:
        """ Return the element dicts corresponding to unmatched steno keys. """
        return self._elems_by_tag["qkey"]

    def rule_elems(self) -> dict:
        """ Return the element dict corresponding to known rule identifiers. """
        return self._elems_by_tag["rule"]

    def base_group(self) -> BoardElement:
        """ Return a group of elements that make up the base present in every stroke. """
        elems = self._elems_by_tag["base"].values()
        first, *others = [*elems] or [BoardElement()]
        return BoardElement(first, *others) if others else first


class BoardGenerator:
    """ Creates graphics for the board diagram. """

    _DEFAULT_RATIO: float = 100.0  # If no aspect ratio is given, this ensures that all boards end up in one row.

    @classmethod
    def build(cls, layout:KeyLayout, rules:Dict[str, StenoRule], board_defs:Dict[str, dict], board_xml:bytes):
        processor = BoardElementProcessor(board_defs)
        root = XMLElement.decode(board_xml)
        parser = BoardElementParser(processor)
        parser.add_recursive(root)
        kfinder = KeyElementFinder(parser.key_elems(), layout)
        ukfinder = KeyElementFinder(parser.unmatched_elems(), layout)
        rule_elems = parser.rule_elems()
        rules_to_elems = {rules[k]: rule_elems[k] for k in rule_elems}
        efinder = ElementFinder(rules_to_elems, kfinder, ukfinder)
        base_group = parser.base_group()
        x, y, w, h = processor.bounds
        factory = BoardFactory(base_group, x, y, w, h)
        return cls(efinder, factory)

    def __init__(self, rfinder:ElementFinder, factory:BoardFactory) -> None:
        self._elem_finder = rfinder
        self._build_document = factory

    def from_keys(self, keys:str, aspect_ratio:float=_DEFAULT_RATIO) -> bytes:
        """ Generate encoded board diagram layouts arranged according to <aspect_ratio> from a set of steno keys. """
        elems = self._elem_finder.from_keys(keys)
        return self._build_document(elems, aspect_ratio)

    def from_rule(self, rule:StenoRule, aspect_ratio:float=_DEFAULT_RATIO, compound=True) -> bytes:
        """ Generate encoded board diagram layouts arranged according to <aspect_ratio> from a steno rule.
            If <compound> is False, do not use compound keys. The rule will be shown only as single keys. """
        if not compound:
            return self.from_keys(rule.keys, aspect_ratio)
        elems = self._elem_finder.from_rule(rule)
        return self._build_document(elems, aspect_ratio)
