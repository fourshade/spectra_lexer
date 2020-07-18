from collections import defaultdict
from typing import Iterable, List, Mapping

from spectra_lexer.lexer.lexer import LexerResult, LexerRule, StenoLexer
from spectra_lexer.lexer.parallel import ParallelMapper
from spectra_lexer.resource.keys import StenoKeyConverter
from spectra_lexer.resource.rules import StenoRule, StenoRuleFactory
from spectra_lexer.resource.translations import ExamplesDict, RuleID, Translation

TranslationPairs = Iterable[Translation]  # Iterable collection of steno translations.


class TranslationFilter:
    """ Size-based filter for RTFCRE steno translations. """

    # Cutoffs for translation filters based on their size.
    SIZE_MINIMUM = 1   # Below this size, the filter blocks everything.
    SIZE_SMALL = 10
    SIZE_MEDIUM = 12
    SIZE_LARGE = 15
    SIZE_MAXIMUM = 20  # At this size and above, the filter is disabled.
    # Ordered list of all filter sizes for GUI display.
    SIZES = [SIZE_MINIMUM, SIZE_SMALL, SIZE_MEDIUM, SIZE_LARGE, SIZE_MAXIMUM]

    def __init__(self, size:int) -> None:
        self._size = size

    def filter(self, translations:TranslationPairs) -> TranslationPairs:
        """ Return only translations where every string is below the maximum size. """
        size = self._size
        if size < self.SIZE_MINIMUM:
            # If the size is below minimum, it could be a dummy run. Keep nothing.
            return []
        elif size >= self.SIZE_MAXIMUM:
            # If the size is maximum, filtering is unnecessary. Keep everything.
            return translations
        else:
            # Eliminate long translations depending on the size factor.
            return [(keys, letters) for keys, letters in translations
                    if len(keys) <= size and len(letters) <= size]


class StenoAnalyzer:
    """ Key-converting wrapper for the lexer. Also uses multiprocessing to make an examples index. """

    # Rule info strings for analysis results.
    INFO_COMPLETE = "Found complete match."
    INFO_INCOMPLETE = "Incomplete match. Not reliable."
    INFO_EMPTY = "No matches found."

    def __init__(self, converter:StenoKeyConverter, lexer:StenoLexer, factory:StenoRuleFactory, rule_sep:StenoRule,
                 refmap:Mapping[LexerRule, StenoRule], idmap:Mapping[LexerRule, RuleID]) -> None:
        self._converter = converter  # Converts between RTFCRE and s-keys formats.
        self._lexer = lexer          # Main analysis engine; operates only on s-keys.
        self._factory = factory      # Creates steno rules from analysis data.
        self._rule_sep = rule_sep    # Stroke separator rule.
        self._refmap = refmap        # Mapping of lexer rule objects to their original StenoRules.
        self._idmap = idmap          # Mapping of lexer rule objects to valid example rule IDs.

    def _to_skeys(self, keys:str) -> str:
        # Convert user RTFCRE steno <keys> to s-keys.
        return self._converter.rtfcre_to_skeys(keys)

    def _to_rtfcre(self, skeys:str) -> str:
        # Convert <skeys> back to RTFCRE format.
        return self._converter.skeys_to_rtfcre(skeys)

    def _result_info(self, result:LexerResult) -> str:
        """ Return an info string for this result. The output is nowhere near reliable if some keys are unmatched. """
        if not result.unmatched_skeys:
            info = self.INFO_COMPLETE
        elif result.rules:
            info = self.INFO_INCOMPLETE
        else:
            info = self.INFO_EMPTY
        return info

    def query(self, keys:str, letters:str, *, strict_mode=False) -> StenoRule:
        """ Return a lexer analysis matching <keys> to <letters> in standard steno rule format.
            If <strict_mode> is True and the best result is missing keys, return a fully unmatched result instead. """
        skeys = self._to_skeys(keys)
        result = self._lexer.query(skeys, letters)
        self._factory.push()
        unmatched_skeys = result.unmatched_skeys
        if strict_mode and unmatched_skeys:
            unmatched_skeys = skeys
        else:
            for lr, start in zip(result.rules, result.rule_positions):
                child = self._refmap[lr]
                length = len(lr.letters)
                self._factory.connect(child, start, length)
        if unmatched_skeys:
            unmatched_keys = self._to_rtfcre(unmatched_skeys)
            nletters = len(letters)
            self._factory.connect_unmatched(unmatched_keys, nletters, "unmatched keys")
        keys = self._to_rtfcre(skeys)
        info = self._result_info(result)
        return self._factory.build(keys, letters, info)

    def best_translation(self, keys_iter:Iterable[str], letters:str) -> str:
        """ Return the best (most accurate) match to <letters> out of <keys_iter> according to lexer ranking. """
        keys_list = list(keys_iter)
        if not keys_list:
            raise ValueError("Cannot find the best of 0 translations.")
        if len(keys_list) == 1:
            best_index = 0
        else:
            skeys_list = [self._to_skeys(keys) for keys in keys_list]
            best_index = self._lexer.best_translation(skeys_list, letters)
        return keys_list[best_index]

    def _query_rule_ids(self, keys:str, letters:str) -> List[str]:
        """ Make a parallel-safe lexer query and return the result as a list of strings.
            Results may be returned out of order, so the output starts with the original keys and letters.
            The identities of rule objects do not survive pickling, so only ID strings are returned.
            Only complete matches should return rule IDs. Rule positions are discarded. """
        skeys = self._to_skeys(keys)
        result = self._lexer.query(skeys, letters)
        output = [keys, letters]
        if not result.unmatched_skeys:
            for lr in result.rules:
                if lr in self._idmap:
                    output.append(self._idmap[lr])
        return output

    def compile_index(self, translations:TranslationPairs, *, size:int=None, process_count=0) -> ExamplesDict:
        """ Run the lexer on all given <translations> with an optional <size> filter.
            This is a big job; do it in parallel if possible using <process_count> processes at once.
            Then make a index containing each rule's ID mapped to a dict of every translation that used it. """
        mapper = ParallelMapper(self._query_rule_ids, process_count=process_count)
        if size is not None:
            translations = TranslationFilter(size).filter(translations)
        results = mapper.starmap(translations)
        index = defaultdict(dict)
        for keys, letters, *rule_ids in results:
            for r_id in rule_ids:
                index[r_id][keys] = letters
        return index

    def join(self, rules:Iterable[StenoRule]) -> StenoRule:
        """ Join several rules into one with stroke separators. """
        rules = list(rules)
        delimited = rules[:1]
        for r in rules[1:]:
            delimited += [self._rule_sep, r]
        return self._factory.join(delimited)

    def normalize_keys(self, keys:str) -> str:
        """ Normalize a set of RTFCRE keys by converting back and forth. """
        skeys = self._to_skeys(keys)
        return self._to_rtfcre(skeys)
