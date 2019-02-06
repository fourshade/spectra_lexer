""" Module for generating steno board diagram elements. """

from typing import Dict, Generator, List

from spectra_lexer.keys import StenoKeys
from spectra_lexer.rules import StenoRule

# Parameters for creating SVG element IDs from steno characters.
SVG_BASE_ID = "Base"


class BoardGenerator:
    """ Generates a list of stroke diagrams, each of which contains a basic background and
        a number of discrete graphical elements representing raw keys and/or simple rules. """

    _rules_dict: Dict[str, StenoRule]     # Saved copy of the rules dict for finding element names.
    _rule_elements: Dict[StenoRule, str]  # Dict mapping steno rule namedtuples to element name strings.

    def __init__(self, rules_dict:Dict[str, StenoRule]):
        self._rules_dict = rules_dict

    def set_rule_elements(self, xml_dict:dict) -> None:
        """ Load a dictionary with each graphical element that has a specific rule. """
        self._rule_elements = {rule: name for name, rule in self._rules_dict.items() if name in xml_dict}

    def generate(self, rule:StenoRule, use_dict:bool=True) -> List[List[str]]:
        """ Generate board diagram elements for a steno rule. """
        if use_dict:
            # For the rule dict to be useful, the rule and its children must be parsed recursively.
            elements = list(self._get_elements(rule))
        else:
            # Without the rule dict, the raw keys can be used without recursion.
            elements = list(rule.keys)
        # Consume any stroke separators to split the elements into strokes.
        strokes = _split_elements(elements)
        # Add the background for each stroke.
        return [[SVG_BASE_ID] + s for s in strokes]

    def _get_elements(self, rule:StenoRule) -> Generator:
        """ Yield board diagram elements from a steno rule recursively. """
        # If the rule itself has an entry in the dict, yield that element and we're done.
        name = self._rule_elements.get(rule)
        if name is not None:
            yield name
            return
        # If the rule has no children and no dict entry, just add raw elements for the keys.
        rulemap = rule.rulemap
        if not rulemap:
            yield from rule.keys
            return
        # Repeat recursively for all children.
        for item in rulemap:
            yield from self._get_elements(item.rule)


def _split_elements(elements:List[str]) -> List[List[str]]:
    """ Split a list of elements at each stroke separator. """
    sep = StenoKeys.separator()
    strokes = []
    start = 0
    for i, element in enumerate(elements):
        if element == sep:
            strokes.append(elements[start:i])
            start = i + 1
    strokes.append(elements[start:])
    return strokes
