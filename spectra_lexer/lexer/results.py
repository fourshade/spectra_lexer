from operator import attrgetter
from typing import Iterable, List, Tuple

from spectra_lexer.keys import StenoKeys
from spectra_lexer.rules import RuleMapItem, StenoRule


class _Result(List[RuleMapItem]):
    """ List-based rulemap: a sequence meant to hold a series of (rule, start, length) tuples
        indicating the various rules that make up a word and their starting/ending positions.
        Map items should be in sequential order by starting position within the word.
        Must be frozen before inclusion in a rule. """

    keys: StenoKeys  # Full key string
    letters: str     # Full English text of the word.

    def __init__(self, keys:StenoKeys, letters:str, src:Iterable[RuleMapItem]=()):
        super().__init__(src)
        self.keys = keys
        self.letters = letters

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

    def rank(self) -> Tuple[int, ...]:
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

    def letters_matched_ratio(self) -> float:
        """ Find total characters matched divided by total characters possible to match (i.e. not spaces). """
        matched = self._letters_matched()
        matchable = sum([c != ' ' for c in self.letters])
        # All whitespace rules shouldn't happen, but let's not ruin someone's day by dividing by zero.
        return matched / matchable if matchable else 0


class LexerResults(list):

    def add(self, keys, word, rulemap):
        """ Add a valid rulemap to the list of results. Requires the full set of keys and letters for ranking. """
        self.append(_Result(keys, word, rulemap))

    def best_map_to_rule(self, default_keys, default_word) -> StenoRule:
        """ Find the best out of a series of rule maps based on the rank value of each and build a rule from it.
            Return an empty rule with the last used translation if no rule maps were found by the lexer. """
        if not self:
            return StenoRule(default_keys, default_word, frozenset(), "No matches found.", ())
        best_result = max(self, key=_Result.rank)
        desc = "Found {:.0%} match.".format(best_result.letters_matched_ratio())
        return StenoRule(best_result.keys, best_result.letters, frozenset(), desc, tuple(best_result))
