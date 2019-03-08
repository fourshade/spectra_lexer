from operator import attrgetter, methodcaller
from typing import List, Generator, NamedTuple, Tuple

from spectra_lexer.steno.keys import StenoKeys
from spectra_lexer.steno.rules import RuleFlags, RuleMapItem, StenoRule

# Flag constants for rule generation.
_RARE_FLAG = RuleFlags.RARE
_UNMATCHED_FLAG_SET = frozenset({RuleFlags.UNMATCHED})
_GENERATED_FLAG_SET = frozenset({RuleFlags.GENERATED})


class LexerResult(NamedTuple):
    """ Container to hold a list-based rulemap from the lexer, with optimized ranking methods.
        The list must be frozen before inclusion in a rule. """

    rulemap: List[RuleMapItem]  # Rulemap from the lexer.
    leftover_keys: StenoKeys    # Unmatched keys left in the map.
    keys: StenoKeys             # Full key string.
    letters: str                # Full English text of the word.

    def letters_matched(self, _get_letters=attrgetter("rule.letters")) -> int:
        """ Get the number of characters matched by mapped rules. """
        return sum(map(len, map(_get_letters, self.rulemap)))

    def letters_matchable(self) -> int:
        """ Get the number of characters possible to match (i.e. not spaces). """
        return sum([c != ' ' for c in self.letters])

    def letters_matched_ratio(self) -> float:
        """ Find total characters matched divided by total characters possible to match (i.e. not spaces). """
        matched = self.letters_matched()
        matchable = self.letters_matchable()
        # All whitespace rules shouldn't happen, but let's not ruin someone's day by dividing by zero.
        return matched / matchable if matchable else 0

    def rare_count(self, _get_flags=attrgetter("rule.flags"), _rare_in=methodcaller("__contains__", _RARE_FLAG)) -> int:
        """ Get the number of rare rules in the map. """
        return sum(map(_rare_in, map(_get_flags, self.rulemap)))

    def rank_diff(self, other) -> Generator:
        """ Generator to find the difference in "rank value" between two lexer-generated rulemaps.
            Used as a lazy sequence-based comparison, with the first non-zero result determining the winner.
            Some criteria are negative, meaning that more accurate maps have smaller values. """
        yield -len(self.leftover_keys) + len(other.leftover_keys)  # Fewest keys unmatched
        yield self.letters_matched()   - other.letters_matched()   # Most letters matched
        yield -self.rare_count()       + other.rare_count()        # Fewest rare rules
        yield -len(self.keys)          + len(other.keys)           # Fewest total keys
        yield -len(self.rulemap)       + len(other.rulemap)        # Fewest child rules

    def __gt__(self, other) -> bool:
        """ Operator for ranking results using max(). Each criterion is lazily evaluated to increase performance. """
        for diff in self.rank_diff(other):
            if diff:
                return diff > 0
        return False

    def to_rule(self) -> StenoRule:
        """ Make a rule out of this map, with a description and possibly a final rule depending on unmatched keys. """
        if not self.leftover_keys:
            desc = f"Found {self.letters_matched_ratio():.0%} match."
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
            bad_rule = StenoRule(self.leftover_keys, "", _UNMATCHED_FLAG_SET, "unmatched keys", ())
            self.rulemap.append(RuleMapItem(bad_rule, last_match_end, len(self.letters) - last_match_end))
        # Freeze the rulemap and mark this rule as lexer-generated.
        return StenoRule(self.keys, self.letters, _GENERATED_FLAG_SET, desc, tuple(self.rulemap))

    @classmethod
    def best_rule(cls, results:list, *, default:Tuple[str,str]=("", "")) -> StenoRule:
        """ Find the best out of a list of results based on the rank value of each and build a rule from it. """
        if results:
            return max(results).to_rule()
        elif default is not None:
            # Make an empty rule with the default pair (after cleansing) if no valid rule maps were added by the lexer.
            keys, word = default
            keys = StenoKeys.cleanse_from_rtfcre(keys)
            return cls([], keys, keys, word).to_rule()
