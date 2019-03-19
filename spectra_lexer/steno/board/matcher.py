""" Module for generating steno board diagram element IDs. """

from typing import Dict, Iterable, Set

from .element import DiagramElements
from spectra_lexer.steno.rules import RuleFlags, StenoRule
from spectra_lexer.utils import save_kwargs

# Format strings for creating SVG element IDs.
_SVG_RULE_FORMAT = ":{}".format
_SVG_UNMATCHED_FORMAT = "{}?".format


class ElementMatcher:
    """ Generates lists of element IDs for stroke diagrams, each of which contains a basic background
        and a number of discrete graphical elements matched to raw keys and/or simple rules. """

    _rule_ids: Dict[StenoRule, str] = {}     # Dict with valid pairs of rules and IDs.

    def set_rules(self, rules_dict:Dict[str, StenoRule]):
        """ Save a dictionary with element ID names of each valid steno rule. """
        self._make_rule_ids(rules={rule: _SVG_RULE_FORMAT(name) for name, rule in rules_dict.items()})

    def set_ids(self, ids:Iterable[str]) -> None:
        """ Save a set of element IDs for which graphics exist. """
        self._make_rule_ids(ids=set(ids))

    @save_kwargs
    def _make_rule_ids(self, *, rules:Dict[StenoRule, str]=None, ids:Set[str]=None) -> None:
        """ Narrow down the final dict to element IDs which exist and have a corresponding rule. """
        if rules and ids:
            self._rule_ids = {rule: name for rule, name in rules.items() if name in ids}

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
