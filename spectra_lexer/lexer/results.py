from operator import attrgetter
from typing import List, Generator, NamedTuple

from spectra_lexer.keys import StenoKeys
from spectra_lexer.rules import RuleFlags, RuleMapItem, StenoRule


class _Result(NamedTuple):
    """ Container to hold a list-based rulemap from the lexer, with optimized ranking methods.
        The list must be frozen before inclusion in a rule. """

    rulemap: List[RuleMapItem]  # Rulemap from the lexer
    keys: StenoKeys             # Full key string.
    letters: str                # Full English text of the word.
    leftover_keys: StenoKeys    # Unmatched keys left in the map.

    def letters_matched(self, _agetter=attrgetter("rule.letters")) -> int:
        """ Get the number of characters matched by mapped rules. """
        return sum(map(len, map(_agetter, self.rulemap)))

    def letters_matchable(self) -> int:
        """ Get the number of characters possible to match (i.e. not spaces). """
        return sum([c != ' ' for c in self.letters])

    def letters_matched_ratio(self) -> float:
        """ Find total characters matched divided by total characters possible to match (i.e. not spaces). """
        matched = self.letters_matched()
        matchable = self.letters_matchable()
        # All whitespace rules shouldn't happen, but let's not ruin someone's day by dividing by zero.
        return matched / matchable if matchable else 0

    def word_coverage(self) -> int:
        """ Return the number of characters between the start of the first child rule and the end of the last. """
        if not self.rulemap:
            return 0
        start_item = self.rulemap[0]
        end_item = self.rulemap[-1]
        return end_item.start + end_item.length - start_item.start

    def rank_diff(self, other) -> Generator:
        """ Generator to find the difference in "rank value" between two lexer-generated rulemaps.
            Used as a lazy sequence-based comparison, with the first non-zero result determining the winner.
            Some criteria are negative, meaning that more accurate maps have smaller values. """
        yield -len(self.leftover_keys) + len(other.leftover_keys)  # Fewest keys unmatched
        yield self.letters_matched()   - other.letters_matched()   # Most letters matched
        yield -len(self.keys)          + len(other.keys)           # Fewest total keys
        yield -len(self.rulemap)       + len(other.rulemap)        # Fewest child rules
        yield -self.word_coverage()    + other.word_coverage()    # End-to-end word coverage

    def __gt__(self, other) -> bool:
        """ Operator for ranking results using max(). Each criterion is lazily evaluated to increase performance. """
        for diff in self.rank_diff(other):
            if diff:
                return diff > 0
        return False

    def to_rule(self) -> StenoRule:
        """ Make a rule out of this map, with a description and possibly a final rule depending on unmatched keys. """
        if not self.leftover_keys:
            desc = "Found {:.0%} match.".format(self.letters_matched_ratio())
        else:
            # If nothing was matched at all, make the description different from a partial failure.
            if not self.rulemap:
                desc = "No matches found."
                last_match_end = 0
            else:
                desc = "Incomplete match. Not reliable."
                last_match = self.rulemap[-1]
                last_match_end = last_match.start + last_match.length
            # Make a special rule with the unmatched keys to cover everything after the last match.
            bad_rule = StenoRule(self.leftover_keys, "", frozenset({RuleFlags.UNMATCHED}), "unmatched keys", ())
            self.rulemap.append(RuleMapItem(bad_rule, last_match_end, len(self.letters) - last_match_end))
        # Freeze the rulemap and mark this rule as lexer-generated.
        return StenoRule(self.keys, self.letters, frozenset({RuleFlags.GENERATED}), desc, tuple(self.rulemap))


class LexerResults(list):
    """ Controller for finished lexer results. Determines which rulemaps are valid
        and creates a rule out of the best result that passes judgement. """

    _need_all_keys: bool  # Do we only keep results that have all keys mapped?

    def __init__(self, need_all_keys:bool=False):
        """ Results may not be required to match every key to be valid. This allows the lexer
            to make partial guesses on difficult translations at the cost of lower performance. """
        super().__init__()
        self._need_all_keys = need_all_keys

    def add_result(self, rulemap:list, keys:StenoKeys, word:str, keys_left:StenoKeys) -> None:
        """ Add a rulemap to the list of results with all required parameters for ranking.
            If we need all keys to be matched, discard incomplete maps. """
        if not keys_left or not self._need_all_keys:
            self.append(_Result(rulemap, keys, word, keys_left))

    def to_rule(self, default_pair:tuple) -> StenoRule:
        """ Find the best out of our current rule maps based on the rank value of each and build a rule from it. """
        if self:
            best_result = max(self)
        else:
            # Make an empty rule with the default pair (after cleansing) if no valid rule maps were added by the lexer.
            keys, word = default_pair
            cleansed = StenoKeys.cleanse_from_rtfcre(keys)
            best_result = _Result([], cleansed, word, cleansed)
        return best_result.to_rule()
