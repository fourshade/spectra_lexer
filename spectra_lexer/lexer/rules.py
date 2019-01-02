from __future__ import annotations
from operator import attrgetter
from typing import Iterable, Sequence

from spectra_lexer.lexer.keys import LexerKeys
from spectra_lexer.rules import RuleMap, StenoRule


class LexerResult(RuleMap):
    """ List-based rulemap builder used during lexer matching. """

    keys: LexerKeys  # Full key string
    letters: str     # Full English text of the word.

    def __init__(self, keys="", letters="", src:Iterable=()):
        super().__init__(src)
        self.keys = keys
        self.letters = letters

    def copy(self):
        return LexerResult(self.keys, self.letters, self)

    def _keys_unmatched(self, agetter=attrgetter("rule.keys")) -> int:
        """ Get the number of keys *not* matched by mapped rules. """
        return sum(map(len, map(agetter, self))) - len(self.keys)

    def _letters_matched(self, agetter=attrgetter("rule.letters")) -> int:
        """ Get the number of characters matched by mapped rules. """
        return sum(map(len, map(agetter, self)))

    def _word_coverage(self) -> int:
        """ Return the number of characters between the start of the first child rule and the end of the last. """
        if self:
            start_item = self[0]
            end_item = self[-1]
            return end_item.start + end_item.length - start_item.start
        return 0

    def rank(self) -> Sequence[int]:
        """
        Determine the "value" of a lexer-generated rulemap.
        A larger value should reflect a more accurate mapping.
        Rank value is determined by a tuple of these values, in order:
            - least keys unmatched
            - most letters matched
            - fewest child rules
            - end-to-end word coverage
        """
        return (self._keys_unmatched(),
                self._letters_matched(),
                -len(self),
                self._word_coverage())

    @classmethod
    def best_map_to_rule(cls, maps:Iterable[LexerResult], default_keys, default_letters) -> StenoRule:
        """ Find the best out of a series of rule maps based on the rank value of each.
            Build and return it, or return the empty map if the iterable is empty. """
        best_result = max(maps, key=cls.rank, default=None)
        if best_result is not None:
            keys = best_result.keys
            letters = best_result.letters
            matchable_letters = sum(c is not ' ' for c in letters)
            if matchable_letters:
                percent_match = best_result._letters_matched() * 100 / matchable_letters
            else:
                percent_match = 0
            desc = "Found {:d}% match.".format(int(percent_match))
            return StenoRule(keys, letters, frozenset(), desc, best_result.freeze())
        else:
            return StenoRule(default_keys, default_letters, frozenset(), "No matches found.", RuleMap().freeze())
