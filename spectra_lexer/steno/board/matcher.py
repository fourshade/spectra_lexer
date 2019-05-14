""" Module for generating steno board diagram element IDs. """

from typing import Callable, Dict, List

from .path import SVGPathInversion
from .svg import SVGElement
from ..rules import RuleFlags, StenoRule


class KeyMatcher:
    """ Matches elements to keys in dicts. """

    _convert_to_skeys: Callable[[str], str]  # Conversion function from RTFCRE to s-keys.
    _dicts: List[Dict[str, SVGElement]]

    def __init__(self, to_skeys:Callable[[str], str],
                 key_dict:Dict[str, SVGElement], unmatched_dict:Dict[str, SVGElement]):
        self._convert_to_skeys = to_skeys
        self._dicts = [key_dict, unmatched_dict]

    def __call__(self, keys:str, unmatched:bool=False) -> List[SVGElement]:
        """ Yield a board diagram element for each raw key. Display question marks for unmatched keys. """
        d = self._dicts[unmatched]
        return [d[k] for k in self._convert_to_skeys(keys)]


class RuleMatcher:
    """ Generates lists of elements for stroke diagrams, each of which contains a basic background
        and a number of discrete graphical elements matched to raw keys and/or simple rules. """

    _key_matcher: KeyMatcher
    _rule_dict: Dict[StenoRule, SVGElement]

    def __init__(self, key_matcher:KeyMatcher, rule_dict:Dict[StenoRule, SVGElement]):
        self._key_matcher = key_matcher
        self._rule_dict = rule_dict

    def __call__(self, rule:StenoRule) -> List[SVGElement]:
        """ Yield board diagram elements from a steno rule recursively. """
        elem = self._rule_dict.get(rule)
        # If the rule itself has an entry in the dict, yield that element and we're done.
        if elem is not None:
            return [elem]
        rulemap = rule.rulemap
        if not rulemap:
            # If the rule has no children and no dict entry, just yield elements for each raw key.
            unmatched = RuleFlags.UNMATCHED in rule.flags
            return self._key_matcher(rule.keys, unmatched)
        # If a rule has children, yield their composition.
        elems = []
        for item in rulemap:
            elems += self(item.rule)
        # Rules using inversions may be drawn with arrows.
        if RuleFlags.INVERSION in rule.flags:
            elems.append(SVGPathInversion(*elems))
        return elems
