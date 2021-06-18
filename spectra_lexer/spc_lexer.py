from collections import defaultdict
from typing import Iterable, List, Mapping

from spectra_lexer.lexer.lexer import LexerResult, LexerRule, StenoLexer
from spectra_lexer.lexer.parallel import ParallelMapper
from spectra_lexer.resource.keys import StenoKeyConverter
from spectra_lexer.resource.rules import StenoRule, StenoRuleFactory
from spectra_lexer.resource.translations import ExamplesDict, RuleID, TranslationsIter


class StenoAnalyzer:
    """ Key-converting wrapper for the lexer. Also uses multiprocessing to make an examples index. """

    # Rule info strings for analysis results. The output is nowhere near reliable if some keys are unmatched.
    INFO_COMPLETE = "Found complete match."
    INFO_INCOMPLETE = "Incomplete match. Not reliable."
    INFO_EMPTY = "No matches found."
    INFO_COMPOUND = "Result of compound analysis."

    def __init__(self, converter:StenoKeyConverter, lexer:StenoLexer, factory:StenoRuleFactory,
                 refmap:Mapping[LexerRule, StenoRule], idmap:Mapping[LexerRule, RuleID], rule_sep:StenoRule) -> None:
        self._converter = converter  # Converts between RTFCRE and s-keys formats.
        self._lexer = lexer          # Main analysis engine; operates only on s-keys.
        self._factory = factory      # Creates steno rules from analysis data.
        self._refmap = refmap        # Mapping of lexer rule objects to their original StenoRules.
        self._idmap = idmap          # Mapping of lexer rule objects to valid example rule IDs.
        self._rule_sep = rule_sep    # Stroke separator rule. Used as a delimiter. Letters are not allowed.

    def _to_skeys(self, keys:str) -> str:
        """ Convert user RTFCRE steno <keys> to s-keys. """
        return self._converter.rtfcre_to_skeys(keys)

    def _to_rtfcre(self, skeys:str) -> str:
        """ Convert <skeys> back to RTFCRE format. """
        return self._converter.skeys_to_rtfcre(skeys)

    def query(self, keys:str, letters:str, *, strict_mode=False) -> StenoRule:
        """ Return a lexer analysis matching <keys> to <letters> in standard steno rule format.
            If <strict_mode> is True and the best result is missing keys, return a fully unmatched result instead. """
        skeys = self._to_skeys(keys)
        result = self._lexer.query(skeys, letters)
        self._factory.push()
        if strict_mode and result.unmatched_skeys:
            result = LexerResult([], [], skeys)
        for lr, start in zip(result.rules, result.rule_positions):
            child = self._refmap[lr]
            length = len(lr.letters)
            self._factory.connect(child, start, length)
        info = self.INFO_COMPLETE
        unmatched_skeys = result.unmatched_skeys
        if unmatched_skeys:
            info = self.INFO_INCOMPLETE if result.rules else self.INFO_EMPTY
            unmatched_keys = self._to_rtfcre(unmatched_skeys)
            nletters = len(letters)
            self._factory.connect_unmatched(unmatched_keys, nletters, "unmatched keys")
        keys = self._to_rtfcre(skeys)
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

    def compound_query(self, translations:TranslationsIter) -> StenoRule:
        """ Perform queries for several translations and flatten the results into one analysis.
            Only translations with keys are analyzed and delimited by stroke separators. """
        all_skeys = all_letters = ""
        sep_skeys = self._to_skeys(self._rule_sep.keys)
        self._factory.push()
        is_first = True
        for keys, letters in translations:
            if keys:
                offset = len(all_letters)
                if not is_first:
                    all_skeys += sep_skeys
                    self._factory.connect(self._rule_sep, offset, 0)
                all_skeys += self._to_skeys(keys)
                rule = self.query(keys, letters)
                for item in rule.rulemap:
                    self._factory.connect(item.child, offset + item.start, item.length)
                is_first = False
            all_letters += letters
        all_keys = self._to_rtfcre(all_skeys)
        return self._factory.build(all_keys, all_letters, self.INFO_COMPOUND)

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

    def compile_index(self, translations:TranslationsIter, *, process_count=0) -> ExamplesDict:
        """ Run the lexer on all given <translations>.
            This is a big job; do it in parallel if possible using <process_count> processes at once.
            Then make a index containing each rule's ID mapped to a dict of every translation that used it. """
        mapper = ParallelMapper(self._query_rule_ids, process_count=process_count)
        results = mapper.starmap(translations)
        index = defaultdict(dict)
        for keys, letters, *rule_ids in results:
            for r_id in rule_ids:
                index[r_id][keys] = letters
        return index
