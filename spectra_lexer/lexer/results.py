from operator import attrgetter
from typing import Iterable, List, Tuple

from spectra_lexer.keys import StenoKeys
from spectra_lexer.rules import RuleMapItem, StenoRule

# TODO: Somehow combine with output flags listing?
_BAD_FLAG_PREFIX = "BAD:"


class _Result(List[RuleMapItem]):
    """ List-based rulemap: a sequence meant to hold a series of (rule, start, length) tuples
        indicating the various rules that make up a word and their starting/ending positions.
        Map items should be in sequential order by starting position within the word.
        Must be frozen before inclusion in a rule. """

    _keys: StenoKeys           # Full key string.
    _letters: str              # Full English text of the word.
    _leftover_keys: StenoKeys  # Unmatched keys left in the map.

    def __init__(self, src:Iterable[RuleMapItem], keys:StenoKeys, letters:str, leftover_keys:StenoKeys):
        super().__init__(src)
        self._keys = keys
        self._letters = letters
        self._leftover_keys = leftover_keys

    def _letters_matched(self, _agetter=attrgetter("rule.letters")) -> int:
        """ Get the number of characters matched by mapped rules. """
        return sum(map(len, map(_agetter, self)))

    def _letters_matchable(self) -> int:
        """ Get the number of characters possible to match (i.e. not spaces). """
        return sum([c != ' ' for c in self._letters])

    def _letters_matched_ratio(self) -> float:
        """ Find total characters matched divided by total characters possible to match (i.e. not spaces). """
        matched = self._letters_matched()
        matchable = self._letters_matchable()
        # All whitespace rules shouldn't happen, but let's not ruin someone's day by dividing by zero.
        return matched / matchable if matchable else 0

    def _word_coverage(self) -> int:
        """ Return the number of characters between the start of the first child rule and the end of the last. """
        if self:
            start_item = self[0]
            end_item = self[-1]
            return end_item.start + end_item.length - start_item.start
        return 0

    def rank(self) -> Tuple[int, ...]:
        """
        Determine the "value" of a lexer-generated rulemap. A larger value should reflect a more accurate mapping.
        Rank value is determined by a tuple of these values, in order:
            - fewest keys unmatched
            - most letters matched
            - fewest child rules
            - end-to-end word coverage
        """
        return -len(self._leftover_keys), self._letters_matched(), -len(self), self._word_coverage()

    def fast_rank(self) -> Tuple[int, ...]:
        """ Omit the key coverage test for cases where only full matches are accepted. """
        return self._letters_matched(), -len(self), self._word_coverage()

    def to_rule(self) -> StenoRule:
        """ Make a rule out of this map, with a description and possibly a final rule depending on unmatched keys. """
        if not self._leftover_keys:
            flags = frozenset()
            desc = "Found {:.0%} match.".format(self._letters_matched_ratio())
        else:
            # If there are any unmatched keys, add a flag telling the output to watch for them.
            flags = frozenset({_BAD_FLAG_PREFIX + self._leftover_keys})
            # If nothing was matched at all, make the description different from a partial failure.
            if not self:
                desc = "No matches found."
            else:
                desc = "Incomplete match. Not reliable."
        return StenoRule(self._keys, self._letters, flags, desc, tuple(self))


class LexerResultManager:
    """ Controller for finished lexer results. Determines which rulemaps are valid
        and creates a rule out of the best result that passes judgement. """

    _list: List[_Result]  # Contains all valid results from the current query.
    _need_all_keys: bool  # Do we only keep maps that have all keys covered?

    def __init__(self, need_all_keys:bool=True):
        """ Results may be required to match every key to be valid. This increases general
            speed at the cost of discarding all partial matches as total failures. """
        self._list = []
        self._need_all_keys = need_all_keys

    def new_query(self) -> None:
        """ Start a new query by dumping all the old results. """
        self._list = []

    def add_result(self, rulemap, keys, word, keys_left) -> None:
        """ Add a rulemap to the list of results with all required parameters for ranking.
            If all rules must have full key coverage, we can discard incomplete maps. """
        if not keys_left or not self._need_all_keys:
            self._list.append(_Result(rulemap, keys, word, keys_left))

    def to_rule(self, default_keys:StenoKeys, default_word:str) -> StenoRule:
        """ Find the best out of our current rule maps based on the rank value of each and build a rule from it.
            If all rules must have full key coverage, use a faster rank test that doesn't check keys. """
        if not self._list:
            # Make an empty result with the last used translation if no valid rule maps were added by the lexer.
            best_result = _Result((), default_keys, default_word, default_keys)
        else:
            rank_fn = _Result.fast_rank if self._need_all_keys else _Result.rank
            best_result = max(self._list, key=rank_fn)
        return best_result.to_rule()
