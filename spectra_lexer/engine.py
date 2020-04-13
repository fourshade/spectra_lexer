from collections import defaultdict
from typing import Tuple

from spectra_lexer.analysis import StenoAnalyzer
from spectra_lexer.display import BoardFactory, GraphFactory, RuleGraph
from spectra_lexer.resource.rules import StenoRule
from spectra_lexer.resource.translations import RTFCREDict, RTFCREExamplesDict
from spectra_lexer.search import SearchEngine, SearchResults
from spectra_lexer.util.parallel import ParallelMapper


class StenoEngine:
    """ Top-level controller for all steno search, analysis, and display components. """

    SEARCH_LIMIT = 100  # Maximum number of matches returned in a search by default.
    INDEX_DELIM = ";"   # Delimiter between rule name and query for example index searches.

    def __init__(self, search_engine:SearchEngine, analyzer:StenoAnalyzer,
                 node_factory:GraphFactory, board_factory:BoardFactory) -> None:
        self._search_engine = search_engine
        self._analyzer = analyzer
        self._graph_factory = node_factory
        self._board_factory = board_factory
        self._translations = RTFCREDict()
        self._examples = RTFCREExamplesDict()

    def load_translations(self, *filenames:str) -> None:
        """ Load and merge translations from JSON files. """
        translations = RTFCREDict.from_json_files(*filenames)
        self.set_translations(translations)

    def set_translations(self, translations:RTFCREDict) -> None:
        """ Send a new translations dict to the search engine. Keep a copy in case we need to make an index. """
        self._translations = translations
        self._search_engine.set_translations(translations)

    def load_examples(self, filename:str) -> None:
        """ Load an examples index from a JSON file. """
        examples = RTFCREExamplesDict.from_json_file(filename)
        self.set_examples(examples)

    def compile_examples(self, size:int=None, **kwargs) -> None:
        """ Run the lexer on all translations with an input filter and look at the top-level rule IDs.
            Make a index with examples of every translation that used each built-in rule. """
        translations = self._translations.size_filtered(size)
        mapper = ParallelMapper(self._analyzer.query_rule_ids, **kwargs)
        results = mapper.starmap(translations.items())
        index = defaultdict(RTFCREDict)
        for keys, letters, *rule_ids in results:
            for r_id in rule_ids:
                index[r_id][keys] = letters
        examples = RTFCREExamplesDict(index)
        self.set_examples(examples)

    def set_examples(self, examples:RTFCREExamplesDict) -> None:
        """ Send a new examples index dict to the search engine. """
        self._examples = examples
        self._search_engine.set_examples(examples)

    def save_examples(self, filename:str) -> None:
        """ Save the current examples index to <filename> as JSON. """
        self._examples.json_dump(filename)

    def search(self, pattern:str, count:int=SEARCH_LIMIT, mode_strokes=False, mode_regex=False) -> SearchResults:
        if self.INDEX_DELIM in pattern:
            link_ref, pattern = pattern.split(self.INDEX_DELIM, 1)
            return self._search_engine.search_examples(link_ref, pattern, count, mode_strokes=mode_strokes)
        return self._search_engine.search_translations(pattern, count, mode_strokes=mode_strokes, mode_regex=mode_regex)

    def has_examples(self, rule_id:str) -> bool:
        return self._search_engine.has_examples(rule_id)

    def random_example(self, rule_id:str, mode_strokes=False) -> Tuple[str, str, str]:
        """ Search for a random example translation using a rule by ID and return it with its search pattern. """
        if not self.has_examples(rule_id):
            return "", "", ""
        keys, letters = self._search_engine.random_example(rule_id)
        match = keys if mode_strokes else letters
        pattern = rule_id + self.INDEX_DELIM + match
        return keys, letters, pattern

    def analyze(self, keys:str, letters:str, strict_mode=False) -> StenoRule:
        """ Run a lexer query on a translation and return the result in rule format. """
        return self._analyzer.query(keys, letters, match_all_keys=strict_mode)

    def analyze_best(self, *translations:Tuple[str, str], strict_mode=False) -> StenoRule:
        """ Run a lexer query on a number of translations and return the best resulting rule. """
        keys, letters = self._analyzer.best_translation(translations)
        return self.analyze(keys, letters, strict_mode)

    def generate_board(self, rule:StenoRule, aspect_ratio:float=None, show_letters=True) -> str:
        """ Generate an encoded board diagram layout for a rule arranged according to <aspect ratio>. """
        return self._board_factory.board_from_rule(rule, aspect_ratio, show_letters)

    def generate_board_from_keys(self, keys:str, aspect_ratio:float=None) -> str:
        """ Generate an encoded board diagram layout for a plain set of keys arranged according to <aspect ratio>. """
        return self._board_factory.board_from_keys(keys, aspect_ratio)

    def generate_graph(self, rule:StenoRule, compressed=True, compat=False) -> RuleGraph:
        """ Generate a graph object for a rule. """
        return self._graph_factory.build(rule, compressed, compat)
