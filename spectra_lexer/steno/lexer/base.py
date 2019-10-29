from typing import Iterable, List, Tuple, TypeVar

# Generic marker for the rule reference data type (may be anything).
RULE_TP = TypeVar("RULE_TP")
# Marker for the match data type: (rule, unmatched keys, rule start, rule length).
MATCH_TP = Tuple[RULE_TP, str, int, int]


class IRuleMatcher:
    """ Interface for a class that matches steno rules using a rule's s-keys and/or letters. """

    def match(self, skeys:str, letters:str, all_skeys:str, all_letters:str) -> Iterable[MATCH_TP]:
        raise NotImplementedError


class CompoundRuleMatcher(IRuleMatcher):
    """ Rule matcher that delegates to children. """

    def __init__(self, *matchers:IRuleMatcher) -> None:
        self._matchers = matchers  # Children that handle the actual matching.

    def match(self, skeys:str, letters:str, all_skeys:str, all_letters:str) -> List[MATCH_TP]:
        """ Return a list of all matches found by any child. """
        matches = []
        for matcher in self._matchers:
            matches += matcher.match(skeys, letters, all_skeys, all_letters)
        return matches
