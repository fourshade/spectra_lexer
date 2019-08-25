from typing import Callable, Dict, List

from .elements import BoardElement, BoardInversionGroup, BoardLinkedGroup, BoardStrokeGap
from ..rules import RuleFlags, StenoRule


class KeyElementFinder:
    """ Contains all elements for a set of steno keys. Uses question marks for unmatched keys. """

    _d: Dict[str, BoardElement]              # Dict with elements for each key.
    _convert_to_skeys: Callable[[str], str]  # Conversion function from RTFCRE to s-keys.

    def __init__(self, key_elems:Dict[str, BoardElement], to_skeys:Callable[[str], str], sep:str) -> None:
        """ Make a stroke sentinel element to match a separator key in any state. """
        key_elems[sep] = BoardStrokeGap()
        self._d = key_elems
        self._convert_to_skeys = to_skeys

    def __call__(self, keys:str) -> List[BoardElement]:
        """ Return a board diagram element for each converted key. """
        d = self._d
        return [d[k] for k in self._convert_to_skeys(keys) if k in d]


class RuleElementFinder:
    """ Dict wrapper for finding board elements by steno rule. """

    _d: Dict[StenoRule, BoardElement]        # Dict with elements for certain rules.
    _matched_key_finder: KeyElementFinder    # Finder for normal steno key elements.
    _unmatched_key_finder: KeyElementFinder  # Finder for steno key elements in unmatched rules.

    def __init__(self, rule_elems:Dict[str, BoardElement], rules:Dict[str, StenoRule],
                 matched_key_finder:KeyElementFinder, unmatched_key_finder:KeyElementFinder) -> None:
        self._d = {rules[k]: rule_elems[k] for k in rule_elems}
        self._matched_key_finder = matched_key_finder
        self._unmatched_key_finder = unmatched_key_finder

    def __call__(self, rule:StenoRule) -> List[BoardElement]:
        """ Return board diagram elements from a steno rule recursively, with a key finder as backup. """
        # If the rule itself has an entry in the dict, just return that element.
        if rule in self._d:
            return [self._d[rule]]
        elems = []
        for item in rule.rulemap:
            elems += self(item.rule)
        if not elems:
            # If the rule has no children and no dict entry, just return elements for each raw key.
            if RuleFlags.UNMATCHED in rule.flags:
                return self._unmatched_key_finder(rule.keys)
            else:
                return self._matched_key_finder(rule.keys)
        # Rules using inversions or linked strokes may be drawn with connectors.
        for f in rule.flags:
            if f == RuleFlags.INVERSION:
                return [BoardInversionGroup(*elems)]
            elif f == RuleFlags.LINKED:
                return [BoardLinkedGroup(*elems)]
        return elems
