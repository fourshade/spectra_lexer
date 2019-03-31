from operator import attrgetter
from typing import Callable, Generator, List, NamedTuple, Tuple

from spectra_lexer.steno.rules import RuleFlags, RuleMapItem, StenoRule

# Flag constants for rule generation.
_RARE_FLAG = RuleFlags.RARE
_UNMATCHED_FLAGS = frozenset({RuleFlags.UNMATCHED})
_GENERATED_FLAGS = frozenset({RuleFlags.GENERATED})


class LexerResult(NamedTuple):
    """ Container to hold a list-based rulemap from the lexer, with optimized ranking methods.
        The list must be frozen before inclusion in a rule. """

    rulemap: List[RuleMapItem]  # Rulemap from the lexer.
    leftover_skeys: str         # Unmatched lexer keys left in the map.
    skeys: str                  # Full lexer key string.
    letters: str                # Full English text of the word.

    def _letters_matched(self, _get_letters=attrgetter("rule.letters")) -> int:
        """ Get the number of characters matched by mapped rules. """
        return sum(map(len, map(_get_letters, self.rulemap)))

    def _letters_matchable(self) -> int:
        """ Get the number of characters possible to match (i.e. not spaces). """
        return sum([c != ' ' for c in self.letters])

    def letters_matched_ratio(self) -> float:
        """ Find total characters matched divided by total characters possible to match (i.e. not spaces). """
        matched = self._letters_matched()
        matchable = self._letters_matchable()
        # All-whitespace rules shouldn't happen, but let's not ruin someone's day by dividing by zero.
        return matchable and matched / matchable

    def _rare_count(self) -> int:
        """ Get the number of rare rules in the map. """
        return sum([_RARE_FLAG in i.rule.flags for i in self.rulemap])

    def _rank_diff(self, other) -> Generator:
        """ Generator to find the difference in "rank value" between two lexer-generated rulemaps.
            Used as a lazy sequence-based comparison, with the first non-zero result determining the winner.
            Some criteria are negative, meaning that more accurate maps have smaller values. """
        yield -len(self.leftover_skeys) + len(other.leftover_skeys)  # Fewest keys unmatched
        yield self._letters_matched()   - other._letters_matched()   # Most letters matched
        yield -self._rare_count()       + other._rare_count()        # Fewest rare rules
        yield -len(self.skeys)          + len(other.skeys)           # Fewest total keys
        yield -len(self.rulemap)        + len(other.rulemap)         # Fewest child rules

    def __gt__(self, other) -> bool:
        """ Operator for ranking results using max(). Each criterion is lazily evaluated to increase performance. """
        for diff in self._rank_diff(other):
            if diff:
                return diff > 0
        return False

    def append(self, rule:StenoRule) -> None:
        """ Add a rule to the end of the map. """
        last_match = self.rulemap[-1]
        last_match_end = last_match.start + last_match.length
        self.rulemap.append(RuleMapItem(rule, last_match_end, len(self.letters) - last_match_end))


class LexerResultRanker:
    """ Takes a set of results from the lexer, finds the best one (if any), converts the keys back to RTFCRE format,
        and creates a new rule with the correct caption and flags. """

    _convert_keys: Callable[[str], str] = str  # Conversion function from s-keys to RTFCRE.

    def set_converter(self, key_converter:Callable[[str],str]):
        self._convert_keys = key_converter

    def best_rule(self, results:List[LexerResult], *, default:Tuple[str,str]=("", "")) -> StenoRule:
        """ Find the best out of a list of results based on the rank value of each and build a rule from it. """
        if not results:
            # Make a fully unmatched rule with the default pair if no valid rule maps were added by the lexer.
            keys, letters = default
            desc = "No matches found."
            bad_rule = StenoRule(keys, "", _UNMATCHED_FLAGS, "unmatched keys", ())
            rulemap = (RuleMapItem(bad_rule, 0, len(letters)),)
        else:
            best = max(results)
            keys = self._convert_keys(best.skeys)
            letters = best.letters
            unmatched = best.leftover_skeys
            if unmatched:
                # Add a special rule with the unmatched keys to cover everything after the last match.
                bad_rule = StenoRule(self._convert_keys(unmatched), "", _UNMATCHED_FLAGS, "unmatched keys", ())
                best.append(bad_rule)
                desc = "Incomplete match. Not reliable."
            else:
                # The caption only shows a percentage if all of the keys were matched.
                desc = f"Found {best.letters_matched_ratio():.0%} match."
            rulemap = tuple(best.rulemap)
        # Freeze the rulemap and make a new rule marked as lexer-generated.
        return StenoRule(keys, letters, _GENERATED_FLAGS, desc, rulemap)
