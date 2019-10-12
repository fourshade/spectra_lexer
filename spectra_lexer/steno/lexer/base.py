""" Contains building blocks for the primary steno analysis component - the lexer.
    Much of the code is inlined for performance reasons. """

from functools import reduce
from typing import Iterable, List, Sequence, Union

from .match import PrefixMatcher, SpecialMatcher, StrokeMatcher, WordMatcher

from ..keys import KeyLayout
from ..rules import StenoRule, RuleMapItem

# Generic marker for the rule data type.
_RULE = StenoRule
# Data type containing the state of the lexer at some point in time. Must be very lightweight.
# Implemented as a list: [keys not yet matched, rule1, rule1_start, rule1_length, rule2, ...]
LexerState = List[Union[StenoRule, str, int]]


class RuleMapper:

    def __init__(self) -> None:
        self._rare_set = set()  # Set of all rules that are considered "rare"

    def set_rare(self, rule:_RULE) -> None:
        """ Set <rule> as being marked as rare."""
        self._rare_set.add(rule)

    def find_best(self, states:Sequence[LexerState], *, match_all_keys=False) -> LexerState:
        """ Rank each of the rule maps in <states> and return the best one. Going in reverse is faster.
            If <match_all_keys> is True, only return results that match every key in the stroke (or the default). """
        assert states
        best = reduce(self._keep_better, reversed(states))
        if best[0] and match_all_keys:
            return states[0]
        return best

    def find_best_index(self, states_seqs:Sequence[Sequence[LexerState]], **kwargs) -> int:
        """ Return the index of the state sequence that has the rule map with the best set of strokes. """
        best_of_each = []
        for seq in states_seqs:
            # If nothing has a complete match, the ranking will end up choosing shorter key sequences
            # over longer ones, even if longer ones matched a higher percentage of keys overall.
            # To get a better result, equalize anything with unmatched keys to have only one.
            unmatched_keys, *rulemap_entries = self.find_best(seq, **kwargs)
            best_of_each.append([unmatched_keys[:1], *rulemap_entries])
        best = self.find_best(best_of_each, **kwargs)
        return best_of_each.index(best)

    def _keep_better(self, current:LexerState, other:LexerState) -> LexerState:
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

    def _rare_diff(self, c:_RULE, o:_RULE) -> int:
        rare_set = self._rare_set
        return (c in rare_set) - (o in rare_set)


class StenoLexer:
    """ The main lexer engine. Uses trial-and-error stack based analysis to gather all possibilities for steno
        patterns it can find, then sorts among them to find what it considers the most likely to be correct. """

    def __init__(self, layout:KeyLayout, rule_sep:_RULE, rule_mapper:RuleMapper,
                 prefix_matcher:PrefixMatcher, special_matcher:SpecialMatcher,
                 stroke_matcher:StrokeMatcher, word_matcher:WordMatcher) -> None:
        """ Build a lexer object from a key layout and rule matchers. """
        self._layout = layout                        # Converts between user RTFCRE steno strings and s-keys.
        self._rule_sep = rule_sep                    # Separator rule constant; is specifically matched on its own.
        self._rule_mapper = rule_mapper              # Ranks lexer rule maps.
        self._match_prefix = prefix_matcher.match    # Matches rules that start with certain keys.
        self._match_special = special_matcher.match  # Matches special rules by reference name.
        self._match_stroke = stroke_matcher.match    # Matches rules by full strokes exactly.
        self._match_word = word_matcher.match        # Matches rules by full words exactly.

    def query(self, keys:str, word:str, **kwargs) -> StenoRule:
        """ Return the best rule that maps the given key string to the given word.
            Thoroughly parse the key string into s-keys format first. """
        skeys = self._layout.from_rtfcre(keys)
        results = self._process(skeys, word)
        unmatched_keys, *rulemap_entries = self._rule_mapper.find_best(results, **kwargs)
        if unmatched_keys:
            # Convert unmatched keys back to RTFCRE format first.
            unmatched_keys = self._layout.to_rtfcre(unmatched_keys)
        it = iter(rulemap_entries)
        rulemap = (*map(RuleMapItem, it, it, it),)
        return StenoRule.generated(keys, word, rulemap, unmatched_keys)

    def best_strokes(self, keys_iter:Iterable[str], word:str, **kwargs) -> str:
        """ Return the best (most accurate) set of strokes from <keys_iter> that matches <word>.
            If nothing matches at all, just return the shortest set of strokes. """
        keys_list = sorted(keys_iter, key=len)
        skeys_iter = map(self._layout.from_rtfcre, keys_list)
        all_results = [self._process(skeys, word) for skeys in skeys_iter]
        best_index = self._rule_mapper.find_best_index(all_results, **kwargs)
        return keys_list[best_index]

    def _process(self, skeys:str, word:str) -> List[LexerState]:
        """ Given a string of formatted s-keys and a matching translation, use steno rules to match keys to printed
            characters in order to generate a series of complete rule maps that could possibly produce the translation.
            Use heavy optimization when possible; add only results that aren't optimized away. """
        # To match sentence beginnings and proper names, the word must be converted to lowercase.
        lword = word.lower()
        lword_find = lword.find
        # In order to test all possibilities, we need a queue or a stack to hold states.
        # Iteration over a list is much faster than popping from a deque. Nothing *actually* gets removed
        # from the list; for practical purposes, the iterator index can be considered the start of the queue.
        # This index starts at 0 and advances every iteration. Appending items in-place does not affect it.
        # The queue starting state has all keys unmatched and no rules.
        q = [[skeys]]
        q_put = q.append
        for skeys_left, *rmap in q:
            if skeys_left:
                # Get the rules that would work as the next match in order from fewest keys matched to most.
                is_start = not rmap
                wordptr = 0 if is_start else rmap[-2] + rmap[-1]
                # If our current stroke is empty, a stroke separator is next. There are no better matches.
                skeys_fs = self._layout.first_stroke(skeys_left)
                if not skeys_fs:
                    q_put([skeys_left[1:], *rmap, self._rule_sep, wordptr, 0])
                    continue
                # Start with a list of all rules that match a prefix of <skeys> and a subset of <letters>.
                letters = lword[wordptr:]
                unordered_set = self._layout.filter_unordered(skeys_fs)
                matches = self._match_prefix(skeys_left, letters, unordered_set)
                # We have a complete stroke next if we just started or a stroke separator was just matched.
                if is_start or rmap[-3] is self._rule_sep:
                    matches += self._match_stroke(skeys_left, letters, skeys_fs)
                # We have a complete word next if we just started or the word pointer is sitting on a space.
                if is_start or letters[:1] == ' ':
                    matches += self._match_word(skeys_left, letters)
                # If we only have unordered keys left at the end of a stroke, look for a special meaning.
                if unordered_set and unordered_set.issuperset(skeys_fs):
                    sep_count = rmap.count(self._rule_sep)
                    matches += self._match_special(skeys_left, skeys_fs, sep_count, word)
                for rule, unmatched_keys, rule_letters in matches:
                    # Find the new location in the word and the number of letters the rule covers.
                    # Add a queue item with the new map, the remaining keys, and the new position in the word.
                    next_wordptr = lword_find(rule_letters, wordptr)
                    q_put([unmatched_keys, *rmap, rule, next_wordptr, len(rule_letters)])
        return q


class LexerFactory:

    def __init__(self, layout:KeyLayout) -> None:
        self._layout = layout
        self._rule_mapper = RuleMapper()
        self._prefix_matcher = PrefixMatcher()
        self._special_matcher = SpecialMatcher()
        self._stroke_matcher = StrokeMatcher()
        self._word_matcher = WordMatcher()

    def add(self, rule:StenoRule) -> None:
        """ Parse keys from each rule into the case-unique s-keys format. """
        skeys = self._layout.from_rtfcre(rule.keys)
        letters = rule.letters
        # Rare rules lose points when deciding the most accurate rule map.
        if rule.is_rare:
            self._rule_mapper.set_rare(rule)
        # Internal rules are only used in special cases, by name.
        if rule.is_special:
            self._special_matcher.add(rule, rule.name)
        # Filter stroke and word rules into their own dicts.
        elif rule.is_stroke:
            self._stroke_matcher.add(rule, skeys, letters)
        elif rule.is_word:
            self._word_matcher.add(rule, skeys, letters)
        # Everything else gets added to the tree-based prefix dictionary.
        else:
            # Unordered keys must be filtered from the first stroke in each string of keys.
            skeys_fs = self._layout.first_stroke(skeys)
            unordered_set = self._layout.filter_unordered(skeys_fs)
            self._prefix_matcher.add(rule, skeys, letters, unordered_set)

    def build_lexer(self, rule_sep:StenoRule) -> StenoLexer:
        """ Create the lexer with the separator and all rule matchers. """
        return StenoLexer(self._layout, rule_sep, self._rule_mapper, self._prefix_matcher, self._special_matcher,
                          self._stroke_matcher, self._word_matcher)
