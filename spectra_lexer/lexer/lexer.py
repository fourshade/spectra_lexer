""" Module for the lexer itself. Much of the code is inlined for performance reasons. """

from operator import attrgetter
from typing import List, Sequence, Tuple, Union

from .base import IRuleMatcher, LexerRule


class LexerResult:
    """ Contains names of rules in a translation, their positions in the word, and leftover keys we couldn't match. """

    def __init__(self, rules:List[LexerRule], rule_positions:List[int], unmatched_skeys:str) -> None:
        self.rules = rules                      # List of the rules found in the translation.
        self.rule_positions = rule_positions    # List of start positions (in the letters) for each rule in order.
        self.unmatched_skeys = unmatched_skeys  # Contains leftover keys we couldn't match.

    def info(self) -> str:
        """ Return an info string for this result. The output is nowhere near reliable if some keys are unmatched. """
        if not self.unmatched_skeys:
            info = "Found complete match."
        elif self.rules:
            info = "Incomplete match. Not reliable."
        else:
            info = "No matches found."
        return info


class StenoLexer:
    """ The main lexer engine. Uses trial-and-error stack based analysis to gather all possibilities for steno
        patterns it can find, then sorts among them to find what it considers the most likely to be correct. """

    # Data type containing the state of the lexer at some point in time. Must be very lightweight.
    # Implemented as a list: [keys_not_yet_matched, word_pointer, rule1, rule1_start, rule2, rule2_start, ...]
    _LexerState = List[Union[str, LexerRule, int]]

    def __init__(self, *rule_matchers:IRuleMatcher) -> None:
        self._matchers = rule_matchers  # Series of steno rule matchers to be called in order.

    def query(self, skeys:str, letters:str) -> LexerResult:
        """ Return a list of the best rules that map <skeys> to <letters>.
            Also return their positions in the word along with anything we couldn't match. """
        unmatched_skeys, _, *rulemap = self._process(skeys, letters)
        return LexerResult(rulemap[::2], rulemap[1::2], unmatched_skeys)

    def find_best_translation(self, translations:Sequence[Tuple[str, str]]) -> int:
        """ Return the index of the best (most accurate) from a sequence of (skeys, letters) <translations>. """
        if not translations:
            raise ValueError("Cannot find the best of 0 translations.")
        if len(translations) == 1:
            return 0
        best_of_each = []
        for skeys, letters in translations:
            # If nothing has a complete match, the ranking will end up choosing shorter key sequences
            # over longer ones, even if longer ones matched a higher percentage of keys overall.
            # To get a better result, equalize anything with unmatched keys to have only one.
            unmatched_keys, *rulemap_entries = self._process(skeys, letters)
            best_of_each.append([unmatched_keys[:1], *rulemap_entries])
        best = self._best_state(best_of_each)
        return best_of_each.index(best)

    def _process(self, skeys:str, letters:str) -> _LexerState:
        """ Given a string of formatted s-keys and a matching translation, use steno rules to match keys to printed
            characters in order to generate a series of rules that could possibly produce the translation. """
        # In order to test all possibilities, we need a queue or a stack to hold states.
        # Iteration over a list is much faster than popping from a deque. Nothing *actually* gets removed
        # from the list; for practical purposes, the iterator index can be considered the start of the queue.
        # This index starts at 0 and advances every iteration. Appending items in-place does not affect it.
        # The queue starting state has all keys unmatched and no rules.
        q = [[skeys, 0]]
        complete = []
        q_put = q.append
        complete_put = complete.append
        for skeys_left, wordptr, *rmap in q:
            letters_left = letters[wordptr:]
            # Gather items from every registered rule matcher.
            for matcher in self._matchers:
                for rule, unmatched_keys, word_offset in matcher.match(skeys_left, letters_left, skeys, letters):
                    # Make a state item with the remaining keys and the rulemap with the new item added.
                    # Add it to the complete results if there are no more keys, otherwise push it on the queue.
                    put = complete_put if not unmatched_keys else q_put
                    next_start = wordptr + word_offset
                    put([unmatched_keys, next_start + len(rule.letters), *rmap, rule, next_start])
        # If we had complete matches, choose the final result from those.
        # Otherwise, look through the queue list. It still contains every item we added to it.
        return self._best_state(complete or q)

    @staticmethod
    def _best_state(states:Sequence[_LexerState], _wt=attrgetter("weight")) -> _LexerState:
        """ Compare all terminated lexer states and return the best one. Going in reverse is faster.
            Each criterion is lazily evaluated, with the first non-zero result determining the winner.
            Some criteria are negative, meaning that more accurate states have smaller values.
            The full compare sequence is inlined to avoid method call overhead. """
        assert states
        best, *others = reversed(states)
        for other in others:
            if (-len(best[0]) + len(other[0]) or                           # Fewest total keys unmatched.
                sum(map(_wt, best[2::2])) - sum(map(_wt, other[2::2])) or  # Highest total rule weight.
               -len(best) + len(other)) < 0:                               # Fewest rules.
                best = other
        return best
