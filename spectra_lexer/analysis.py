from collections import defaultdict
from typing import Iterable, List, Mapping, Tuple

from spectra_lexer.lexer import LexerResult, LexerRule, StenoLexer
from spectra_lexer.lexer.composite import PriorityRuleMatcher
from spectra_lexer.lexer.exact import StrokeMatcher, WordMatcher
from spectra_lexer.lexer.prefix import UnorderedPrefixMatcher
from spectra_lexer.lexer.special import DelimiterMatcher, SpecialMatcher
from spectra_lexer.resource.keys import StenoKeyConverter
from spectra_lexer.resource.rules import StenoRule, StenoRuleCollection
from spectra_lexer.util.parallel import ParallelMapper

TranslationPairs = Iterable[Tuple[str, str]]  # Iterable collection of (keys, letters) steno translations.


class StenoAnalyzer:
    """ Key-converting wrapper for the lexer. Also uses multiprocessing to make an examples index. """

    def __init__(self, converter:StenoKeyConverter, lexer:StenoLexer,
                 refmap:Mapping[LexerRule, StenoRule], idmap:Mapping[LexerRule, str]) -> None:
        self._to_skeys = converter.rtfcre_to_skeys   # Converts user RTFCRE steno strings to s-keys.
        self._to_rtfcre = converter.skeys_to_rtfcre  # Converts s-keys back to RTFCRE.
        self._lexer = lexer                          # Main analysis engine; operates only on s-keys.
        self._refmap = refmap                        # Mapping of lexer rule objects to their original StenoRules.
        self._idmap = idmap                          # Mapping of lexer rule objects to valid example rule IDs.

    def query(self, keys:str, letters:str, *, strict_mode=False) -> StenoRule:
        """ Return a lexer analysis matching <keys> to <letters> in standard steno rule format.
            If <strict_mode> is True and the best result is missing keys, return a fully unmatched result instead. """
        skeys = self._to_skeys(keys)
        result = self._lexer.query(skeys, letters)
        info = self._result_info(result)
        rule = StenoRule.analysis(keys, letters, info)
        unmatched_skeys = result.unmatched_skeys
        last_match_end = 0
        if strict_mode and unmatched_skeys:
            unmatched_skeys = skeys
        else:
            for lr, start in zip(result.rules, result.rule_positions):
                child = self._refmap[lr]
                length = len(lr.letters)
                last_match_end = start + length
                rule.add_connection(child, start, length)
        if unmatched_skeys:
            ur = StenoRule.unmatched(self._to_rtfcre(unmatched_skeys))
            rule.add_connection(ur, last_match_end, len(letters) - last_match_end)
        return rule

    @staticmethod
    def _result_info(result:LexerResult) -> str:
        """ Return an info string for this result. The output is nowhere near reliable if some keys are unmatched. """
        if not result.unmatched_skeys:
            info = "Found complete match."
        elif result.rules:
            info = "Incomplete match. Not reliable."
        else:
            info = "No matches found."
        return info

    def best_translation(self, translations:TranslationPairs) -> Tuple[str, str]:
        """ Return the best (most accurate) from a series of <translations> according to lexer ranking. """
        translations = list(translations)
        converted = [(self._to_skeys(keys), letters) for keys, letters in translations]
        best_index = self._lexer.find_best_translation(converted)
        return translations[best_index]

    def compile_index(self, translations:TranslationPairs, *, process_count=0) -> Mapping[str, TranslationPairs]:
        """ Run the lexer on all given <translations>. This is a big job; do it in parallel if possible.
            Make a index containing each rule's ID mapped to a list of every translation that used it. """
        mapper = ParallelMapper(self._query_rule_ids, process_count=process_count)
        results = mapper.starmap(translations)
        index = defaultdict(list)
        for keys, letters, *rule_ids in results:
            translation = keys, letters
            for r_id in rule_ids:
                index[r_id].append(translation)
        return index

    def _query_rule_ids(self, keys:str, letters:str) -> List[str]:
        """ Make a lexer query and return the rule IDs in a list with their matching keys and letters.
            Only fully matched translations should have any rule IDs returned.
            This output format works well for parallel operations because:
                - results may be returned out of order, so the matching input is saved with the output.
                - StenoRule objects are recursive structures that pickle poorly, so only the IDs are saved. """
        skeys = self._to_skeys(keys)
        result = self._lexer.query(skeys, letters)
        output = [keys, letters]
        if not result.unmatched_skeys:
            for lr in result.rules:
                if lr in self._idmap:
                    output.append(self._idmap[lr])
        return output

    @classmethod
    def from_resources(cls, converter:StenoKeyConverter, rules:StenoRuleCollection,
                       key_sep:str, unordered_keys:str) -> "StenoAnalyzer":
        """ Distribute rules and build the rule matcher, lexer and analyzer. """
        sep_matcher = DelimiterMatcher()
        stroke_matcher = StrokeMatcher(key_sep)
        word_matcher = WordMatcher()
        prefix_matcher = UnorderedPrefixMatcher(key_sep, unordered_keys)
        special_matcher = SpecialMatcher(key_sep)
        refmap = {}
        idmap = {}
        for rule in rules:
            # Convert each rule to lexer format. Rule weight is assigned based on letters matched.
            # Rare rules are uncommon in usage and/or prone to causing false positives.
            # They have slightly reduced weight so that other rules with equal letter count are chosen first.
            skeys = converter.rtfcre_to_skeys(rule.keys)
            letters = rule.letters
            weight = 10 * len(letters) - rule.is_rare
            lr = LexerRule(skeys, letters, weight)
            # Map every lexer-format rule to the original so we can convert back.
            refmap[lr] = rule
            # Add the lexer rule to one of the rule matchers based on flags.
            r_id = rule.id
            if rule.is_special:
                # Rules with special behavior must be handled case-by-case.
                if skeys == key_sep:
                    sep_matcher.add(lr)
                else:
                    special_matcher.add_by_id(lr, r_id)
            else:
                # Rules without special behavior should be in example indices.
                idmap[lr] = r_id
                if rule.is_reference:
                    # Reference-only rules are not matched directly.
                    pass
                elif rule.is_stroke:
                    # Stroke rules are matched only by complete strokes.
                    stroke_matcher.add(lr)
                elif rule.is_word:
                    # Word rules are matched only by whole words (but still case-insensitive).
                    word_matcher.add(lr)
                else:
                    # All other rules are added to the tree-based prefix matcher.
                    prefix_matcher.add(lr)
        # Separators are force-matched before the normal matchers can waste cycles on them.
        # Use the special matcher only if absolutely nothing else has worked.
        matcher = PriorityRuleMatcher([sep_matcher],
                                      [prefix_matcher, stroke_matcher, word_matcher],
                                      [special_matcher])
        lexer = StenoLexer(matcher)
        return cls(converter, lexer, refmap, idmap)
