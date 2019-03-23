""" Module for generating steno board diagram element IDs. """

from typing import Dict, Iterable

from .element import DiagramElements
from spectra_lexer.steno.rules import RuleFlags, StenoRule

# Format strings for creating SVG element IDs.
_SVG_RULE_FORMAT = ":{}".format
_SVG_UNMATCHED_FORMAT = "{}?".format


class ElementMatcher:
    """ Generates lists of element IDs for stroke diagrams, each of which contains a basic background
        and a number of discrete graphical elements matched to raw keys and/or simple rules. """

    _rule_ids: Dict[StenoRule, str] = {}     # Dict with valid pairs of rules and IDs.

    def set_rule_ids(self, rules:Dict[str, StenoRule], ids:Iterable[str]) -> None:
        """ Make the final dict using only element IDs which exist and have a corresponding rule. """
        svg_rules = zip(map(_SVG_RULE_FORMAT, rules), rules.values())
        id_set = set(ids)
        self._rule_ids = {rule: name for name, rule in svg_rules if name in id_set}

    def get_element_ids(self, rule:StenoRule, use_dict:bool=True) -> DiagramElements:
        """ Generate board diagram element IDs for a steno rule recursively. """
        # Without the rule dict, the raw key names can be used without recursion.
        return DiagramElements(self._elements_from_rule(rule) if use_dict else rule.keys)

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
        if rule.flags and RuleFlags.UNMATCHED in rule.flags:
            return map(_SVG_UNMATCHED_FORMAT, rule.keys)
        # If the rule has no children and no dict entry, just add element IDs for each raw key.
        return rule.keys
