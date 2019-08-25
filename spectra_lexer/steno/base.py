""" The primary steno analysis engine. Generates rules from translations and creates visual representations. """

from functools import lru_cache
from typing import Dict, List

from .analyzer import IndexMapper, StenoAnalyzer
from .board import BoardGenerator
from .graph import GraphGenerator
from .lexer import StenoLexer
from .keys import KeyLayout
from .parallel import FilterMapper
from .rules import StenoRule
from .search import SearchEngine


class StenoEngine:

    _board: BoardGenerator
    _graph: GraphGenerator
    _lexer: StenoLexer
    _search: SearchEngine
    _analyzer: StenoAnalyzer

    def __init__(self, layout:KeyLayout, rules:Dict[str, StenoRule], board_defs:dict, board_xml:bytes) -> None:
        """ Load all static resources into steno components. """
        self._board = BoardGenerator(layout, rules, board_defs, board_xml)
        self._graph = GraphGenerator(layout)
        self._lexer = StenoLexer(layout, rules)
        self._search = SearchEngine(rules)
        self._analyzer = StenoAnalyzer(rules)
        # Delegate methods for view-based operations. Add caches to the most expensive and/or frequently called ones.
        # Only components with invariant state and methods with immutable output are allowed to have caches.
        self.lexer_query = lru_cache()(self._lexer.query)
        self.lexer_best_strokes = self._lexer.best_strokes
        self.graph_generate = lru_cache()(self._graph.generate)
        self.board_from_keys = lru_cache()(self._board.from_keys)
        self.board_from_rule = lru_cache()(self._board.from_rule)
        self.search_query = self._search.search
        self.search_examples = self._search.find_example
        self.search_links = self._search.rule_to_link
        self.search_rules = self._search.link_to_rule

    def set_translations(self, translations:Dict[str, str]) -> None:
        """ Send this translations dict to all required components. """
        self._search.load_translations(translations)
        self._analyzer.load_translations(translations.items())

    def set_index(self, index:Dict[str, dict]) -> None:
        """ Send this index dict to all required components. """
        self._search.load_index(index)

    def make_rules(self, *args, **kwargs) -> List[StenoRule]:
        """ Run the lexer on every item in a steno translations dictionary. """
        mapper = FilterMapper(self._lexer.query, *args, **kwargs)
        return self._analyzer.make_rules(mapper)

    def make_index(self, *args, match_all_keys=True, **kwargs) -> Dict[str, dict]:
        """ Generate a set of rules from translations using the lexer and compare them to the built-in rules.
            Make a index for each built-in rule containing a dict of every translation that used it.
            Only keep results with all keys matched by default to reduce garbage. """
        mapper = IndexMapper(self._lexer.query, *args, match_all_keys=match_all_keys, **kwargs)
        return self._analyzer.make_index(mapper)
