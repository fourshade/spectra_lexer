""" Module for storing and sorting lexer state structures. """

from functools import reduce
from typing import List, Sequence, TypeVar, Union

# Generic marker for the rule reference data type.
_RULE = TypeVar("_RULE")
# Data type containing the state of the lexer at some point in time. Must be very lightweight.
# Implemented as a list: [keys not yet matched, rule1, rule1_start, rule1_length, rule2, ...]
LexerState = List[Union[_RULE, str, int]]


class RuleMapper:

    def __init__(self) -> None:
        self._rare_set = set()  # Set of all rules that are considered "rare"

    def set_rare(self, rule:_RULE) -> None:
        """ Set <rule> as being marked as rare."""
        self._rare_set.add(rule)

    def find_best(self, states:Sequence[LexerState]) -> LexerState:
        """ Rank each of the rule maps in <states> and return the best one. Going in reverse is faster. """
        assert states
        return reduce(self._keep_better, reversed(states))

    def find_best_index(self, states_seqs:Sequence[Sequence[LexerState]]) -> int:
        """ Return the index of the state sequence that has the rule map with the best set of strokes. """
        best_of_each = []
        for seq in states_seqs:
            # If nothing has a complete match, the ranking will end up choosing shorter key sequences
            # over longer ones, even if longer ones matched a higher percentage of keys overall.
            # To get a better result, equalize anything with unmatched keys to have only one.
            unmatched_keys, *rulemap_entries = self.find_best(seq)
            best_of_each.append([unmatched_keys[:1], *rulemap_entries])
        best = self.find_best(best_of_each)
        return best_of_each.index(best)

    def _keep_better(self, current:LexerState, other:LexerState) -> LexerState:
        """ Foldable function that keeps one of two lexer states based on which has a greater "value".
            Each criterion is lazily evaluated, with the first non-zero result determining the winner.
            Some criteria are negative, meaning that more accurate maps have smaller values.
            As it is called repeatedly by reduce(), the full compare sequence
            is inlined to avoid method call overhead. """
        if (-len(current[0]) + len(other[0]) or                        # Fewest keys unmatched
            sum(current[3::3]) - sum(other[3::3]) or                   # Most letters matched
            -sum(map(self._rare_diff, current[1::3], other[1::3])) or  # Fewest rare child rules
            -len(current) + len(other)) >= 0:                          # Fewest child rules
            return current
        return other

    def _rare_diff(self, c:_RULE, o:_RULE) -> int:
        rare_set = self._rare_set
        return (c in rare_set) - (o in rare_set)
