""" Contains the primary steno analysis component - the lexer. Much of the code is inlined for performance reasons. """

from functools import reduce
from typing import List, Iterable, Sequence, Tuple, Union

from .base import IRuleMatcher, RULE_ID


class LexerResult:
    """ Contains names of rules in a translation, their positions in the word, and leftover keys we couldn't match. """

    def __init__(self, rule_ids:List[RULE_ID], rule_positions:List[int], unmatched_skeys:str) -> None:
        self._rule_ids = rule_ids
        self._rule_positions = rule_positions
        self._unmatched_skeys = unmatched_skeys

    def rule_ids(self) -> List[str]:
        """ Return a list of ID references to the rules found in the translation. """
        return self._rule_ids

    def rule_positions(self) -> List[int]:
        """ Return a list of start positions (in the letters) for each rule we found in order. """
        return self._rule_positions

    def unmatched_skeys(self) -> str:
        """ Return any leftover keys we couldn't match. """
        return self._unmatched_skeys


class StenoLexer:
    """ The main lexer engine. Uses trial-and-error stack based analysis to gather all possibilities for steno
        patterns it can find, then sorts among them to find what it considers the most likely to be correct.
        All steno key input is required to be in 's-keys' string format, which has the following requirements:

        - Every key in a stroke is represented by a single distinct character (in contrast to RTFCRE).
        - Strokes are delimited by a single distinct character.
        - The keys within each stroke must be sorted according to some total ordering (i.e. steno order). """

    # Data type containing the state of the lexer at some point in time. Must be very lightweight.
    # Implemented as a list: [keys_not_yet_matched, rule1_id, rule1_start, rule1_length, rule2_id, ...]
    _STATE_TP = List[Union[str, RULE_ID, int]]

    def __init__(self, rule_matcher:IRuleMatcher, rare_rules:Iterable[RULE_ID]=()) -> None:
        self._match = rule_matcher.match   # Method of main rule matcher (may be compound).
        self._rare_set = set(rare_rules)   # Set of all rules that are considered "rare"

    def query(self, skeys:str, letters:str, *, match_all_keys=False) -> LexerResult:
        """ Return a list of the best rules that map <skeys> to <letters>.
            Also return their positions in the word along with anything we couldn't match. """
        unmatched_skeys, *rulemap = self._process(skeys, letters)
        if match_all_keys and unmatched_skeys:
            # If <match_all_keys> is True and the best result is missing some, return a fully unmatched result instead.
            rulemap = []
            unmatched_skeys = skeys
        return LexerResult(rulemap[::3], rulemap[1::3], unmatched_skeys)

    def find_best_translation(self, translations:Sequence[Tuple[str, str]]) -> int:
        """ Return the index of the best (most accurate) translation from a sequence of (skeys, word) translations. """
        best_of_each = []
        for skeys, word in translations:
            # If nothing has a complete match, the ranking will end up choosing shorter key sequences
            # over longer ones, even if longer ones matched a higher percentage of keys overall.
            # To get a better result, equalize anything with unmatched keys to have only one.
            unmatched_keys, *rulemap_entries = self._process(skeys, word)
            best_of_each.append([unmatched_keys[:1], *rulemap_entries])
        best = self._find_best(best_of_each)
        return best_of_each.index(best)

    def _process(self, skeys:str, letters:str) -> _STATE_TP:
        """ Given a string of formatted s-keys and a matching translation, use steno rules to match keys to printed
            characters in order to generate a series of rules that could possibly produce the translation. """
        # In order to test all possibilities, we need a queue or a stack to hold states.
        # Iteration over a list is much faster than popping from a deque. Nothing *actually* gets removed
        # from the list; for practical purposes, the iterator index can be considered the start of the queue.
        # This index starts at 0 and advances every iteration. Appending items in-place does not affect it.
        # The queue starting state has all keys unmatched and no rules.
        q = [[skeys]]
        q_put = q.append
        for skeys_left, *rmap in q:
            if skeys_left:
                wordptr = 0 if not rmap else rmap[-2] + rmap[-1]
                letters_left = letters[wordptr:]
                match_iter = self._match(skeys_left, letters_left, skeys, letters)
                for rule_id, unmatched_keys, rule_start, rule_length in match_iter:
                    # Add a queue item with the remaining keys and the rulemap with the new item added.
                    q_put([unmatched_keys, *rmap, rule_id, rule_start + wordptr, rule_length])
        return self._find_best(q)

    def _find_best(self, states:Sequence[_STATE_TP]) -> _STATE_TP:
        """ Rank each of the rule maps in <states> and return the best one. Going in reverse is faster. """
        assert states
        return reduce(self._keep_better, reversed(states))

    def _keep_better(self, current:_STATE_TP, other:_STATE_TP) -> _STATE_TP:
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

    def _rare_diff(self, c:RULE_ID, o:RULE_ID) -> int:
        rare_set = self._rare_set
        return (c in rare_set) - (o in rare_set)
