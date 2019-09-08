from functools import lru_cache
import random
from typing import Dict, List, Tuple

from .analysis import IndexInfo, ParallelMapper
from .board import BoardElementParser, BoardEngine
from .graph import GraphGenerator
from .keys import KeyLayout
from .lexer import StenoLexer
from .rules import RuleParser, StenoRule
from .search import IndexSearchDict, TranslationsSearchDict


class StenoEngine:
    """ Main access point for steno analysis. Generates rules from translations and creates visual representations.
        Uses specially created search dictionaries to find translations using a variety of methods. """

    INDEX_DELIM: str = ";"  # Delimiter between rule name and query for index searches.

    def __init__(self, rule_parser:RuleParser, board:BoardEngine, graph:GraphGenerator, lexer:StenoLexer) -> None:
        """ Delegate methods for view-based operations. Add caches to the most expensive and/or frequently called ones.
            Only components with invariant state and methods with immutable output are allowed to have caches. """
        self._rule_parser = rule_parser  # Parses rules from JSON and keeps track of the refs for inverse parsing.
        self._board = board
        self._graph = graph
        self._lexer = lexer
        self._translations = TranslationsSearchDict()
        self._index = IndexSearchDict()
        self.board_from_keys = lru_cache()(board.from_keys)
        self.board_from_rule = lru_cache()(board.from_rule)
        self.graph_generate = lru_cache()(graph.generate)
        self.lexer_query = lru_cache()(lexer.query)
        self.lexer_best_strokes = lexer.best_strokes

    def set_translations(self, translations:Dict[str, str]) -> None:
        """ Load a new translations search dict. """
        self._translations = TranslationsSearchDict(translations)

    def set_index(self, index:Dict[str, dict]) -> None:
        """ Load a new search index.  Make sure it is a dict of dicts and not arbitrary JSON. """
        if type(index) is not dict or not all([type(v) is dict for v in index.values()]):
            raise TypeError("All first-level values in an index must be dicts.")
        self._index = IndexSearchDict(index)

    def search(self, pattern:str, match:str=None, **kwargs) -> List[str]:
        """ Choose an index to use based on delimiters in the input pattern.
            Search for matches in that index. If <match> is given, the search will find mappings instead. """
        *keys, pattern = pattern.split(self.INDEX_DELIM, 1)
        index = self._index if keys else self._translations
        return index.search(*keys, match or pattern, **kwargs)

    def find_example(self, link:str, strokes:bool=False) -> Tuple[str, str]:
        """ Given a rule by name, find one translation using it at random. Return it with the required input text. """
        d = self._index.get(link) or {"": ""}
        k = random.choice(list(d))
        selection = k if strokes else d[k]
        text = self.INDEX_DELIM.join([link, selection])
        return selection, text

    def rule_to_link(self, rule:StenoRule) -> str:
        """ Return the name of the given rule to use in a link, but only if it has examples in the index. """
        name = self._rule_parser.get_name(rule)
        return name if name in self._index else ""

    def link_to_rule(self, link:str) -> StenoRule:
        """ Return the rule under the given link name, or None if there is no rule by that name. """
        return self._rule_parser.get(link)

    def make_rules(self, **kwargs) -> Dict[str, list]:
        """ Run the lexer on all translations and return a list of raw rules for saving. """
        mapper = ParallelMapper(self._lexer.query, **kwargs)
        results = mapper.starmap(self._translations.items())
        return self._rule_parser.compile_to_raw(results)

    def make_index(self, size:int, match_all_keys=True, **kwargs) -> Dict[str, dict]:
        """ Make a index from a parallel lexer query operation, using input and output filters to control size.
            Only keep results with all keys matched by default to reduce garbage. """
        info = IndexInfo(size)
        mapper = ParallelMapper(self._lexer.query, match_all_keys=match_all_keys, **kwargs)
        translations_in = info.filter_in(self._translations.items())
        results = mapper.starmap(translations_in)
        results_out = info.filter_out(results)
        return self._rule_parser.compile_tr_index(results_out)


class StenoResources:
    """ Contains all static resources necessary for a steno system. The structures are mostly JSON dicts.
        Assets including a key layout, rules, and (optional) board graphics comprise the system. """

    def __init__(self, raw_layout:dict, raw_rules:Dict[str, list],
                 board_defs:Dict[str, dict], board_elems:Dict[str, dict]) -> None:
        """ All fields are static steno resources loaded from package assets. """
        self.raw_layout = raw_layout
        self.raw_rules = raw_rules
        self.board_defs = board_defs
        self.board_elems = board_elems

    def build_engine(self) -> StenoEngine:
        """ Load all static resources into steno components and create an engine with them. """
        layout = KeyLayout(self.raw_layout)
        rule_parser = RuleParser(self.raw_rules)
        rules = rule_parser.to_dict()
        board_parser = BoardElementParser(self.board_defs)
        board_parser.parse(self.board_elems)
        board = board_parser.build_engine(layout, rules)
        graph = GraphGenerator(layout.SEP)
        lexer = StenoLexer(layout)
        lexer.update(rules)
        return StenoEngine(rule_parser, board, graph, lexer)
