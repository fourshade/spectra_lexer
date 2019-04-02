""" Module for generating steno board diagram element IDs. """

from typing import Callable, Dict, Iterable, List

from spectra_lexer.steno.rules import RuleFlags, StenoRule
from spectra_lexer.steno.system import StenoSystem

# Format strings for creating SVG element IDs.
_SVG_RULE_PREFIX = ":"
_SVG_UNMATCHED_SUFFIX = "?"
# Pre-made element IDs.
_BACKGROUND_IDS = ["Base"]


class ElementMatcher:
    """ Generates lists of element IDs for stroke diagrams, each of which contains a basic background
        and a number of discrete graphical elements matched to raw keys and/or simple rules. """

    _rule_ids: Dict[StenoRule, str]          # Dict with valid pairs of rules and IDs.
    _convert_to_skeys: Callable[[str], str]  # Conversion function from RTFCRE to s-keys.
    _key_sep: str                            # Steno key used as stroke separator in both stroke formats.

    def __init__(self, system:StenoSystem) -> None:
        """ Make the dict using only element IDs which exist and have a corresponding rule. """
        id_set = set(system.board["id"])
        self._rule_ids = {r: _SVG_RULE_PREFIX + n for n, r in system.rules.items() if _SVG_RULE_PREFIX + n in id_set}
        self._convert_to_skeys = system.from_rtfcre
        self._key_sep = system.keys.SEP

    def get_element_ids(self, rule:StenoRule, use_dict:bool=True) -> List[List[str]]:
        """ Generate board diagram element IDs for a steno rule recursively. """
        # Without the rule dict, the raw key names can be used without recursion.
        if use_dict:
            elements = self._elements_from_rule(rule)
        else:
            elements = self._convert_to_skeys(rule.keys)
        return self.make_element_lists(elements)

    def _elements_from_rule(self, rule:StenoRule) -> Iterable:
        """ Return board diagram elements from a steno rule recursively. """
        name = self._rule_ids.get(rule)
        # If the rule itself has an entry in the dict, yield that element and we're done.
        if name is not None:
            return [name]
        # If the rule has children, return their composition.
        if rule.rulemap:
            elements = []
            for item in rule.rulemap:
                elements += self._elements_from_rule(item.rule)
            return elements
        # If the rule is for unmatched keys, display question marks instead of the key names.
        skeys = self._convert_to_skeys(rule.keys)
        if RuleFlags.UNMATCHED in rule.flags:
            return [k + _SVG_UNMATCHED_SUFFIX if k != self._key_sep else k for k in skeys]
        # If the rule has no children and no dict entry, just add element IDs for each raw key.
        return skeys

    def make_element_lists(self, elements:Iterable[str]) -> List[List[str]]:
        """ Split an iterable of elements at each stroke separator and add the background to each stroke. """
        lists = []
        elements = list(elements)
        start = 0
        for i, element in enumerate(elements):
            if self._key_sep == element:
                lists.append(_BACKGROUND_IDS + elements[start:i])
                start = i + 1
        lists.append(_BACKGROUND_IDS + elements[start:])
        return lists
