""" Contains building blocks for the primary steno analysis component - the lexer.
    Much of the code is inlined for performance reasons. """

from typing import List, Sequence, Tuple

from .match import PrefixMatcher, SpecialMatcher, StrokeMatcher, WordMatcher
from .state import LexerState, RuleMapper


class LexerResult:
    """ Contains names of rules in a translation, their positions in the word, and leftover keys we couldn't match. """

    def __init__(self, state:LexerState) -> None:
        self._state = state

    def unmatched_skeys(self) -> str:
        """ Return any leftover keys we couldn't match. """
        return self._state[0]

    def rule_names(self) -> List[str]:
        """ Return a list of reference names to the rules found in the translation. """
        return self._state[1::3]

    def rule_positions(self) -> List[int]:
        """ Return a list of start positions (in the letters) for each rule we found. """
        return self._state[2::3]

    def rule_lengths(self) -> List[int]:
        """ Return a list of lengths (in the letters) for each rule we found. """
        return self._state[3::3]

    def __iter__(self) -> zip:
        """ Yield the rulemap in (name, start, length) tuples. """
        it = iter(self._state[1:])
        return zip(it, it, it)

    def caption(self) -> str:
        """ Return the caption for a lexer result. """
        unmatched_skeys, *rulemap = self._state
        if not unmatched_skeys:
            caption = "Found complete match."
        # The output is nowhere near reliable if some keys couldn't be matched.
        elif rulemap:
            caption = "Incomplete match. Not reliable."
        else:
            caption = "No matches found."
        return caption


class StenoLexer:
    """ The main lexer engine. Uses trial-and-error stack based analysis to gather all possibilities for steno
        patterns it can find, then sorts among them to find what it considers the most likely to be correct.
        All steno key input is required to be in 's-keys' string format, which has the following requirements:

        - Every key in a stroke is represented by a single distinct character (in contrast to RTFCRE).
        - Strokes are delimited by a single distinct character.
        - The keys within each stroke must be sorted according to some total ordering (i.e. steno order). """

    def __init__(self, key_sep:str, unordered_keys="") -> None:
        """ Build a lexer object from a key filter and rule matchers. """
        self._rule_mapper = RuleMapper()                      # Creates rule maps from lexer results.
        self._prefix_matcher = PrefixMatcher(key_sep, unordered_keys)  # Matches rules that start with certain keys.
        self._stroke_matcher = StrokeMatcher(key_sep)         # Matches rules by full strokes exactly.
        self._word_matcher = WordMatcher()                    # Matches rules by full words exactly.
        self._special_matcher = SpecialMatcher(key_sep, unordered_keys)  # Matches special rules by reference name.

    def add_prefix_rule(self, *args) -> None:
        """ Rules should be added to the tree-based prefix dictionary by default. """
        self._prefix_matcher.add(*args)

    def add_rare_rule(self, name:str, skeys:str, letters:str) -> None:
        """ Rare rules are prefix rules that are uncommon in usage and/or prone to causing false positives.
            They are worth less when deciding the most accurate rule map. """
        self._rule_mapper.set_rare(name)
        self.add_prefix_rule(name, skeys, letters)

    def add_stroke_rule(self, *args) -> None:
        """ Stroke rules are matched only by complete strokes. """
        self._stroke_matcher.add(*args)

    def add_word_rule(self, *args) -> None:
        """ Word rules are matched only by whole words as delimited by whitespace (but still case-insensitive). """
        self._word_matcher.add(*args)

    def add_special_rule(self, name:str) -> None:
        """ Special rules are only used in certain end cases, by name (which also serves as the identifier). """
        self._special_matcher.add(name, name)

    def query(self, skeys:str, word:str) -> LexerResult:
        """ Return a list of the best rules that map <skeys> to <word>.
            Also return their positions in the word along with anything we couldn't match. """
        results = self._process(skeys, word)
        state = self._rule_mapper.find_best(results)
        return LexerResult(state)

    def find_best_translation(self, translations:Sequence[Tuple[str, str]]) -> int:
        """ Return the index of the best (most accurate) translation from a sequence of (skeys, word) translations. """
        all_states = [self._process(skeys, word) for skeys, word in translations]
        return self._rule_mapper.find_best_index(all_states)

    def _process(self, skeys:str, letters:str) -> List[LexerState]:
        """ Given a string of formatted s-keys and a matching translation, use steno rules to match keys to printed
            characters in order to generate a series of rule maps that could possibly produce the translation. """
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
                matches = []
                matches += self._prefix_matcher.match(skeys_left, letters_left, skeys, letters)
                matches += self._stroke_matcher.match(skeys_left, letters_left, skeys, letters)
                matches += self._word_matcher.match(skeys_left, letters_left, skeys, letters)
                matches += self._special_matcher.match(skeys_left, letters_left, skeys, letters)
                for rule, unmatched_keys, rule_start, rule_length in matches:
                    # Add a queue item with the remaining keys and the rulemap with the new item added.
                    q_put([unmatched_keys, *rmap, rule, rule_start + wordptr, rule_length])
        return q
