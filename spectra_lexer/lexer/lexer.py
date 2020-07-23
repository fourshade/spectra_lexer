""" Module for the lexer itself. Much of the code is inlined for performance reasons. """

from operator import attrgetter
from typing import List, Sequence, Union

from . import IRule, IRuleMatcher


class LexerRule(IRule):
    """ Lexer rule data sortable by weight. """

    def __init__(self, skeys:str, letters:str, weight:int) -> None:
        self.skeys = skeys      # Steno keys matched by the rule, in "s-keys" format (one unique character per key).
        self.letters = letters  # Orthographic characters (i.e. English letters) matched by the rule.
        self.weight = weight    # Weighting level for accuracy comparisons.

    def __repr__(self) -> str:
        return f'LexerRule{(self.skeys, self.letters, self.weight)!r}'


class LexerResult:
    """ Contains names of rules in a translation, their positions in the word, and leftover keys we couldn't match. """

    def __init__(self, rules:List[LexerRule], rule_positions:List[int], unmatched_skeys:str) -> None:
        self.rules = rules                      # List of the rules found in the translation.
        self.rule_positions = rule_positions    # List of start positions (in the letters) for each rule in order.
        self.unmatched_skeys = unmatched_skeys  # Contains leftover keys we couldn't match.


class _LexerStates:
    """ Container for choosing good results from complete and/or terminated lexer states. """

    # Data type containing the state of the lexer at some point in time. Must be very lightweight.
    # Implemented as a list: [keys_not_yet_matched, rule1, rule1_start, rule2, rule2_start, ...]
    _LexerState = List[Union[str, LexerRule, int]]

    def __init__(self, states:Sequence[_LexerState]) -> None:
        assert states
        self._states = states

    def best(self, _wt=attrgetter("weight")) -> _LexerState:
        """ Compare all lexer states and return the best one.
            Each criterion is lazily evaluated, with the first non-zero result determining the winner.
            Some criteria are negative, meaning that more accurate states have smaller values.
            The full compare sequence is inlined to avoid method call overhead. """
        best, *others = self._states
        for other in others:
            if (-len(best[0]) + len(other[0]) or                           # Fewest total keys unmatched.
                sum(map(_wt, best[1::2])) - sum(map(_wt, other[1::2])) or  # Highest total rule weight.
               -len(best) + len(other)) < 0:                               # Fewest rules.
                best = other
        return best


class StenoLexer:
    """ The main lexer engine. Uses trial-and-error stack based analysis to gather all possibilities for steno
        patterns it can find, then sorts among them to find what it considers the most likely to be correct. """

    def __init__(self, rule_matcher:IRuleMatcher) -> None:
        self._rule_matcher = rule_matcher  # Root rule matcher (most likely a composite).

    def query(self, skeys:str, letters:str) -> LexerResult:
        """ Return a list of the best rules that map <skeys> to <letters>,
            their positions in the word, and any keys we couldn't match. """
        states = self._process(skeys, letters)
        unmatched_skeys, *rulemap = states.best()
        return LexerResult(rulemap[::2], rulemap[1::2], unmatched_skeys)

    def best_translation(self, skeys_seq:Sequence[str], letters:str) -> int:
        """ Return the index of the best (most accurate) set of keys in <skeys_seq> that maps to <letters>. """
        assert skeys_seq
        best_of_each = []
        for skeys in skeys_seq:
            # If nothing has a complete match, the ranking will end up choosing shorter key sequences
            # over longer ones, even if longer ones matched a higher percentage of keys overall.
            # To get a better result, equalize anything with unmatched keys to have only one.
            states = self._process(skeys, letters)
            unmatched_keys, *rulemap = states.best()
            best_of_each.append([unmatched_keys[:1], *rulemap])
        best = _LexerStates(best_of_each).best()
        return best_of_each.index(best)

    def _process(self, skeys:str, letters:str) -> _LexerStates:
        """ Given a string of formatted s-keys and a matching translation, use steno rules to match keys to printed
            characters in order to generate a series of rules that could possibly produce the translation. """
        # In order to test all possibilities, we need a queue or a stack to hold states.
        # Iteration over a list is much faster than popping from a deque. Nothing *actually* gets removed
        # from the list; for practical purposes, the iterator index can be considered the start of the queue.
        # This index starts at 0 and advances every iteration. Appending items in-place does not affect it.
        # The queue starting state has all keys unmatched and no rules. At the end it has all incomplete matches.
        q = [[skeys]]
        complete = []
        q_put = q.append
        complete_put = complete.append
        match_rules = self._rule_matcher.match
        wordptr = 0
        for skeys_left, *rmap in q:
            if rmap:
                wordptr = rmap[-1] + len(rmap[-2].letters)
            letters_left = letters[wordptr:]
            for rule, unmatched_keys, word_offset in match_rules(skeys_left, letters_left, skeys, letters):
                # Make a state item with the remaining keys and the rulemap with the new item added.
                # Add it to the complete results if there are no more keys, otherwise push it on the queue.
                state = [unmatched_keys, *rmap, rule, wordptr + word_offset]
                if unmatched_keys:
                    q_put(state)
                else:
                    complete_put(state)
        # There is no need to rank incomplete matches unless we didn't find any complete ones.
        return _LexerStates(complete or q)
