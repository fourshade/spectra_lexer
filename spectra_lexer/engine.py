from typing import Tuple

from spectra_lexer.analysis import StenoAnalyzer, StenoRuleCollection
from spectra_lexer.display import BoardFactory, GraphFactory, RuleGraph
from spectra_lexer.resource.board import StenoBoardDefinitions
from spectra_lexer.resource.keys import StenoKeyLayout
from spectra_lexer.resource.rules import StenoRule
from spectra_lexer.resource.translations import RTFCREDict, RTFCREExamplesDict
from spectra_lexer.search import MatchDict, SearchEngine


class StenoEngine:
    """ Top-level controller for all steno search, analysis, and display components. """

    INDEX_DELIM = ";"  # Delimiter between rule name and query for example index searches.

    def __init__(self, search_engine:SearchEngine, analyzer:StenoAnalyzer,
                 node_factory:GraphFactory, board_factory:BoardFactory) -> None:
        self._search_engine = search_engine
        self._analyzer = analyzer
        self._graph_factory = node_factory
        self._board_factory = board_factory
        self._translations = RTFCREDict()
        self._examples = RTFCREExamplesDict()

    def set_translations(self, translations:RTFCREDict) -> None:
        """ Send a new translations dict to the search engine. Keep a copy in case we need to make an index. """
        self._translations = translations
        self._search_engine.set_translations(translations)

    def load_translations(self, *filenames:str) -> None:
        """ Load and merge translations from JSON files. """
        translations = RTFCREDict.from_json_files(*filenames)
        self.set_translations(translations)

    def set_examples(self, examples:RTFCREExamplesDict) -> None:
        """ Send a new examples index dict to the search engine. """
        self._examples = examples
        self._search_engine.set_examples(examples)

    def load_examples(self, filename:str) -> None:
        """ Load an examples index from a JSON file. """
        examples = RTFCREExamplesDict.from_json_file(filename)
        self.set_examples(examples)

    def search(self, pattern:str, count:int=None, mode_strokes=False, mode_regex=False) -> MatchDict:
        if self.INDEX_DELIM in pattern:
            link_ref, pattern = pattern.split(self.INDEX_DELIM, 1)
            return self._search_engine.search_examples(link_ref, pattern, count, mode_strokes=mode_strokes)
        if mode_regex:
            return self._search_engine.search_regex(pattern, count, mode_strokes=mode_strokes)
        return self._search_engine.search(pattern, count, mode_strokes=mode_strokes)

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
        return self._analyzer.query(keys, letters, strict_mode=strict_mode)

    def best_translation(self, *translations:Tuple[str, str]) -> Tuple[str, str]:
        return self._analyzer.best_translation(translations)

    def compile_examples(self, size:int=None, filename:str=None, process_count=0) -> None:
        """ Run the lexer on all translations with an optional <size> filter and look at the top-level rule IDs.
            Make a index with examples of every translation that used each built-in rule and set it as active.
            If a <filename> is given, save the index as JSON at the end. """
        translations = self._translations
        if size is not None:
            translations = translations.size_filtered(size)
        index = self._analyzer.compile_index(translations.items(), process_count=process_count)
        examples = RTFCREExamplesDict(zip(index, map(RTFCREDict, index.values())))
        self.set_examples(examples)
        if filename is not None:
            examples.json_dump(filename)

    def generate_board(self, rule:StenoRule, aspect_ratio:float=None, show_letters=True) -> str:
        return self._board_factory.board_from_rule(rule, aspect_ratio, show_letters=show_letters)

    def generate_board_from_keys(self, keys:str, aspect_ratio:float=None) -> str:
        return self._board_factory.board_from_keys(keys, aspect_ratio)

    def generate_graph(self, rule:StenoRule, compressed=True, compat=False) -> RuleGraph:
        return self._graph_factory.build(rule, compressed=compressed, compat=compat)

    @classmethod
    def from_resources(cls, keymap:StenoKeyLayout, rules:StenoRuleCollection,
                       board_defs:StenoBoardDefinitions) -> "StenoEngine":
        """ Build a complete engine from a set of required resources. """
        key_parser = keymap.make_parser()
        search_engine = SearchEngine()
        analyzer = StenoAnalyzer.from_resources(key_parser, rules, keymap.sep, keymap.unordered)
        graph_factory = GraphFactory(keymap.sep, keymap.split)
        board_factory = BoardFactory.from_resources(key_parser, board_defs, keymap.unordered[-1:])
        return cls(search_engine, analyzer, graph_factory, board_factory)
