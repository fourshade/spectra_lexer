from typing import Dict, List

from .elements import BoardElement, BoardInversionGroup, BoardLinkedGroup, BoardStrokeGap
from ..keys import KeyLayout
from ..rules import StenoRule


class KeyElementFinder:
    """ Contains all elements for a set of steno keys. Uses question marks for unmatched keys. """

    def __init__(self, key_elems:Dict[str,BoardElement], layout:KeyLayout) -> None:
        """ Make a stroke sentinel element to match a separator key in any state. """
        key_elems[layout.SEP] = BoardStrokeGap()
        self._d = key_elems                          # Dict with elements for each key.
        self._convert_to_skeys = layout.from_rtfcre  # Conversion function from RTFCRE to s-keys.

    def __call__(self, keys:str) -> List[BoardElement]:
        """ Return a board diagram element for each converted key. """
        d = self._d
        return [d[k] for k in self._convert_to_skeys(keys) if k in d]


class ElementFinder:
    """ Dict wrapper for finding board elements by either key string or steno rule. """

    def __init__(self, rules_to_elems:Dict[StenoRule, BoardElement],
                 matched_key_finder:KeyElementFinder, unmatched_key_finder:KeyElementFinder) -> None:
        self._d = rules_to_elems                              # Dict with elements for certain rules.
        self._matched_key_finder = matched_key_finder         # Finder for normal steno key elements.
        self._unmatched_key_finder = unmatched_key_finder     # Finder for steno key elements in unmatched rules.

    def from_keys(self, keys:str) -> List[BoardElement]:
        """ Return board diagram elements from an ordinary steno key string. No special elements will be used. """
        return self._matched_key_finder(keys)

    def from_rule(self, rule:StenoRule) -> List[BoardElement]:
        """ Return board diagram elements from a steno rule recursively, with a key finder as backup. """
        # If the rule itself has an entry in the dict, just return that element.
        if rule in self._d:
            return [self._d[rule]]
        elems = []
        for item in rule.rulemap:
            elems += self.from_rule(item.rule)
        flags = rule.flags
        if not elems:
            # If the rule has no children and no dict entry, just return elements for each raw key.
            if flags.unmatched:
                return self._unmatched_key_finder(rule.keys)
            else:
                return self._matched_key_finder(rule.keys)
        if flags:
            # Rules using inversions or linked strokes may be drawn with connectors.
            if flags.inversion:
                return [BoardInversionGroup(*elems)]
            elif flags.linked:
                return [BoardLinkedGroup(*elems)]
        return elems
