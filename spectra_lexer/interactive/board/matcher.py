""" Module for generating steno board diagram element IDs. """

from typing import Dict, Generator, List

from spectra_lexer.keys import StenoKeys
from spectra_lexer.rules import StenoRule, RuleFlags

# Parameters for creating SVG element IDs.
_SVG_RULE_PREFIX = ":"
_SVG_UNMATCHED_SUFFIX = "?"
# Pre-made element IDs.
_SEP_ID = StenoKeys.separator()
_BACKGROUND_ID = "Base"
_UNMATCHED_IDS = {k: k + _SVG_UNMATCHED_SUFFIX for k in StenoKeys.full_stroke()}
_UNMATCHED_IDS[_SEP_ID] = _SEP_ID


class ElementMatcher:
    """ Generates lists of element IDs for stroke diagrams, each of which contains a basic background
        and a number of discrete graphical elements matched to raw keys and/or simple rules. """

    _rule_elements: Dict[StenoRule, str] = {}  # Dict matching steno rule namedtuples to element ID strings.

    def set_rules(self, rules_dict:Dict[str, StenoRule]):
        """ Load a dictionary with element ID names of each rule. """
        self._rule_elements = {rule: _SVG_RULE_PREFIX + name for name, rule in rules_dict.items()}

    def set_ids(self, id_dict:dict) -> None:
        """ Narrow the rules dict down to only element IDs which actually exist. """
        self._rule_elements = {rule: name for rule, name in self._rule_elements.items() if name in id_dict}

    def get_element_ids(self, rule:StenoRule, use_dict:bool=True) -> List[List[str]]:
        """ Generate board diagram element IDs for a steno rule. """
        if use_dict:
            # For the rule dict to be useful, the rule and its children must be parsed recursively.
            elements = list(self._elements_from_rule(rule))
        else:
            # Without the rule dict, the raw key names can be used without recursion.
            elements = list(rule.keys)
        # Consume stroke separators to split the elements into strokes and add the background for each one.
        return [[_BACKGROUND_ID] + s for s in _split_elements(elements)]

    def _elements_from_rule(self, rule:StenoRule) -> Generator:
        """ Yield board diagram elements from a steno rule recursively. """
        name = self._rule_elements.get(rule)
        if name is not None:
            # If the rule itself has an entry in the dict, yield that element and we're done.
            yield name
        elif rule.rulemap:
            # Yield the composition of all children from this rule.
            for item in rule.rulemap:
                yield from self._elements_from_rule(item.rule)
        else:
            # If the rule has no children and no dict entry, just add element IDs for each raw key.
            if RuleFlags.UNMATCHED in rule.flags:
                # If the rule is for unmatched keys, display question marks instead of the key names.
                yield from [_UNMATCHED_IDS[k] for k in rule.keys]
            else:
                yield from rule.keys


def _split_elements(elements:List[str]) -> Generator:
    """ Split a list of elements at each stroke separator. """
    start = 0
    for i, element in enumerate(elements):
        if element == _SEP_ID:
            yield elements[start:i]
            start = i + 1
    yield elements[start:]
