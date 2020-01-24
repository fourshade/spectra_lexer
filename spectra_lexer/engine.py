from collections import defaultdict
from typing import Tuple

from spectra_lexer.analysis import StenoAnalyzer
from spectra_lexer.display import DisplayData, DisplayEngine, DisplayOptions
from spectra_lexer.resource import RTFCREDict, RTFCREExamplesDict, StenoRule
from spectra_lexer.search import SearchEngine, SearchResults
from spectra_lexer.util.parallel import ParallelMapper


class SearchOptions:
    """ Namespace for steno search options. """

    search_mode_strokes: bool = False  # If True, search for strokes instead of translations.
    search_mode_regex: bool = False    # If True, perform search using regex characters.
    search_match_limit: int = 100      # Maximum number of matches returned on one page of a search.


class AnalyzerOptions:
    """ Namespace for lexer options. """

    lexer_strict_mode: bool = False  # Only return lexer results that match every key in a translation.


class StenoEngine:
    """ Top-level controller for all steno search, analysis, and display components. """

    _INDEX_DELIM = ";"  # Delimiter between rule name and query for example index searches.

    def __init__(self, search_engine:SearchEngine, analyzer:StenoAnalyzer, display_engine:DisplayEngine) -> None:
        self._search_engine = search_engine
        self._analyzer = analyzer
        self._display_engine = display_engine
        self._translations = RTFCREDict()

    def set_search_translations(self, translations:RTFCREDict) -> None:
        """ Send a new translations dict to the search engine. Keep a copy in case we need to make an index. """
        self._translations = translations
        self._search_engine.set_translations(translations)

    def set_search_examples(self, examples:RTFCREExamplesDict) -> None:
        """ Send a new examples index dict to the search engine. """
        self._search_engine.set_examples(examples)

    def make_index(self, size:int=None, **kwargs) -> RTFCREExamplesDict:
        """ Run the lexer on all translations with an input filter and look at the top-level rule IDs.
            Make a index containing a dict for each built-in rule with every translation that used it. """
        translations = self._translations.size_filtered(size)
        mapper = ParallelMapper(self._analyzer.query_rule_ids, **kwargs)
        results = mapper.starmap(translations.items())
        index = defaultdict(RTFCREDict)
        for keys, letters, *rule_ids in results:
            for r_id in rule_ids:
                index[r_id][keys] = letters
        return RTFCREExamplesDict(index)

    def search(self, pattern:str, pages=1, options=SearchOptions()) -> SearchResults:
        count = pages * options.search_match_limit
        mode_strokes = options.search_mode_strokes
        if self._INDEX_DELIM in pattern:
            link_ref, pattern = pattern.split(self._INDEX_DELIM, 1)
            results = self._search_engine.search_examples(link_ref, pattern, count, mode_strokes=mode_strokes)
        else:
            results = self._search_engine.search_translations(pattern, count, mode_strokes=mode_strokes,
                                                              mode_regex=options.search_mode_regex)
        return results

    def random_example(self, rule_id:str, options=SearchOptions()) -> Tuple[str, str, str]:
        """ Search for a random example translation using a rule by ID and return it with its search pattern. """
        if not self._search_engine.has_examples(rule_id):
            return "", "", ""
        keys, letters = self._search_engine.random_example(rule_id)
        match = keys if options.search_mode_strokes else letters
        pattern = rule_id + self._INDEX_DELIM + match
        return keys, letters, pattern

    def analyze(self, keys:str, letters:str, options=AnalyzerOptions()) -> StenoRule:
        """ Run a lexer query on a translation and return the result in rule format. """
        return self._analyzer.query(keys, letters, match_all_keys=options.lexer_strict_mode)

    def analyze_best(self, *translations:Tuple[str, str], options=AnalyzerOptions()) -> StenoRule:
        """ Run a lexer query on a number of translations and return the best resulting rule. """
        keys, letters = self._analyzer.best_translation(translations)
        return self.analyze(keys, letters, options)

    def display(self, analysis:StenoRule, options=DisplayOptions()) -> DisplayData:
        """ Return visual representations of a translation analysis (or any steno rule) with graphs and boards.
            Remove links to any rules for which we don't have examples. """
        data = self._display_engine.process(analysis, options)
        for page in [data.default_page, *data.pages_by_ref.values()]:
            if not self._search_engine.has_examples(page.rule_id):
                page.rule_id = ""
        return data
