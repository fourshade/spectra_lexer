""" Module for generating steno board diagram elements. """

from typing import Dict, Generator, List

from spectra_lexer.keys import StenoKeys
from spectra_lexer.rules import StenoRule, RuleFlags

# Parameters for creating SVG element IDs.
SVG_BASE_ID = "Base"
SVG_RULE_PREFIX = ":"


class BoardGenerator:
    """ Generates a list of stroke diagrams, each of which contains a basic background and
        a number of discrete graphical elements representing raw keys and/or simple rules. """

    _rules_dict: Dict[str, StenoRule]     # Saved copy of the rules dict for finding element names.
    _rule_elements: Dict[StenoRule, str]  # Dict mapping steno rule namedtuples to element name strings.
    _sep: StenoKeys                       # Pre-made stroke separator.

    def __init__(self, rules_dict:Dict[str, StenoRule]):
        self._rules_dict = rules_dict
        self._sep = StenoKeys.separator()

    def set_rule_elements(self, xml_dict:dict) -> None:
        """ Load a dictionary with each graphical element that has a specific rule. """
        self._rule_elements = {rule: SVG_RULE_PREFIX + name
                               for name, rule in self._rules_dict.items() if SVG_RULE_PREFIX + name in xml_dict}

    def generate(self, rule:StenoRule, use_dict:bool=True) -> List[List[str]]:
        """ Generate board diagram elements for a steno rule. """
        if use_dict:
            # For the rule dict to be useful, the rule and its children must be parsed recursively.
            elements = list(self._get_elements(rule))
        else:
            # Without the rule dict, the raw keys can be used without recursion.
            elements = list(rule.keys)
        # Consume any stroke separators to split the elements into strokes.
        strokes = self._split_elements(elements)
        # Add the background for each stroke.
        return [[SVG_BASE_ID] + s for s in strokes]

    def _get_elements(self, rule:StenoRule) -> Generator:
        """ Yield board diagram elements from a steno rule recursively. """
        name = self._rule_elements.get(rule)
        if name is not None:
            # If the rule itself has an entry in the dict, yield that element and we're done.
            yield name
        elif rule.rulemap:
            # Yield the composition of all children from this rule.
            for item in rule.rulemap:
                yield from self._get_elements(item.rule)
        else:
            # If the rule has no children and no dict entry, just add raw elements for the keys.
            if RuleFlags.UNMATCHED in rule.flags:
                # If the rule is for unmatched keys, display question marks instead of the key names.
                yield from [k + "?" if k != self._sep else k for k in rule.keys]
            else:
                yield from rule.keys

    def _split_elements(self, elements:List[str]) -> List[List[str]]:
        """ Split a list of elements at each stroke separator. """
        sep = self._sep
        strokes = []
        start = 0
        for i, element in enumerate(elements):
            if element == sep:
                strokes.append(elements[start:i])
                start = i + 1
        strokes.append(elements[start:])
        return strokes
