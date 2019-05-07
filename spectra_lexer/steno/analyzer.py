from collections import defaultdict
from typing import Callable, Dict, List, Iterable

from .rules import StenoRule
from spectra_lexer.core import Component

# Default size of generated indices (maximum word size).
_DEFAULT_INDEX_SIZE = 12


class StenoAnalyzer(Component):
    """ The primary batch steno analysis engine. Queries the lexer in bulk and creates indices. """

    rev_rules = resource("system:rev_rules", {})
    translations = resource("translations", {})

    @on("analyzer_make_rules")
    def make_rules(self, filter_in:Callable=None, filter_out:Callable=None) -> List[StenoRule]:
        """ Run the lexer on all currently loaded translations and return a list of results.
            <filter_in> eliminates translations before processing, and <filter_out> eliminates results afterward. """
        in_filtered = filter(filter_in, self.translations.items())
        results = self.engine_call("lexer_query_all", in_filtered)
        out_filtered = list(filter(filter_out, results))
        self.engine_call("new_analysis", out_filtered)
        return out_filtered

    @on("analyzer_make_index")
    def make_index(self, size:int=_DEFAULT_INDEX_SIZE) -> Dict[str, dict]:
        """ Generate a set of rules from translations using the lexer and compare them to the built-in rules.
            Make a index for each built-in rule containing a dict of every translation that used it. """
        filter_in, filter_out = self._make_filters(size)
        results = self.make_rules(filter_in, filter_out)
        d = self._compile_results(results)
        self.engine_call("new_index", d)
        return d

    def _make_filters(self, size:int) -> tuple:
        """ Generate filters to control index size. Larger words are excluded with smaller index sizes.
            The parameter <size> determines the relative size of a generated index (range 1-20). """
        def filter_in(translation, max_length=size) -> bool:
            """ Filter function to eliminate larger entries from the index depending on the size factor. """
            return max(map(len, translation)) <= max_length
        def filter_out(rule) -> bool:
            """ Filter function to eliminate lexer results that are unmatched or basic rules themselves. """
            return len(rule.rulemap) > 1
        return (filter_in if size < 20 else None), filter_out

    def _compile_results(self, results:Iterable[StenoRule]) -> Dict[str, dict]:
        """ From lexer rulemaps, make dicts of all translations that use each built-in rule at the top level. """
        tr_dicts = defaultdict(dict)
        for rs in results:
            keys = rs.keys
            letters = rs.letters
            for item in rs.rulemap:
                tr_dicts[item.rule][keys] = letters
        # Convert the rule keys to strings. Hardcoded and missing rules will map to None.
        index = {self.rev_rules.get(k): v for k, v in tr_dicts.items()}
        # Entries with no rule are useless, and None/null is not a valid key in JSON, so toss it.
        if None in index:
            del index[None]
        return index
