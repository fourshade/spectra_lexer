from typing import Callable, List, Tuple

from .elements import BoardElement, BoardInversionGroup, BoardLinkedGroup, BoardStrokeGap
from spectra_lexer.resource import RulesDictionary, RuleFlags, StenoRule


class KeyElementFinder:
    """ Contains all elements for a set of steno keys. Uses question marks for unmatched keys. """

    _d: dict                                 # Dict with elements for each key.
    _convert_to_skeys: Callable[[str], str]  # Conversion function from RTFCRE to s-keys.

    def __init__(self, key_elems:dict, to_skeys:Callable[[str], str], sep:str):
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

    # Certain rule flags indicate the creation of special element groups.
    _FLAG_GROUPS = {RuleFlags.INVERSION: BoardInversionGroup,
                    RuleFlags.LINKED:    BoardLinkedGroup}

    _d: dict                               # Dict with elements for certain rules.
    _key_finders: Tuple[KeyElementFinder]  # Element finders for steno keys when matched[0] or unmatched[1].

    def __init__(self, rule_elems:dict, rules:RulesDictionary, *key_finders:KeyElementFinder):
        self._d = {rules[k]: rule_elems[k] for k in rule_elems}
        self._key_finders = key_finders

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
            return self._key_finders[RuleFlags.UNMATCHED in rule.flags](rule.keys)
        # Rules using inversions or linked strokes may be drawn with connectors.
        for f in rule.flags:
            if f in self._FLAG_GROUPS:
                return [self._FLAG_GROUPS[f](*elems)]
        return elems
