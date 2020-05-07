""" Module for matching rules by delegation to other rule matchers. """

from typing import Iterable, List

from .base import IRuleMatcher, RuleMatch


class PriorityRuleMatcher(IRuleMatcher):
    """ Composite rule matcher containing groups of other rule matchers ordered by priority. """

    def __init__(self, *matcher_groups:Iterable[IRuleMatcher]) -> None:
        self._groups = matcher_groups  # Groups of steno rule matchers to be tried in iteration order.

    def match(self, skeys:str, letters:str, all_skeys:str, all_letters:str) -> List[RuleMatch]:
        """ Look for matches using each group of rule matchers in priority order.
            If a group finds matches, return all of the matches found by that group and stop.
            Only move to the next group if the previous group finds nothing at all. """
        matches = []
        for group in self._groups:
            for matcher in group:
                matches += matcher.match(skeys, letters, all_skeys, all_letters)
            if matches:
                break
        return matches
