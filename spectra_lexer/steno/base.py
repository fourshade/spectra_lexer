from functools import lru_cache
import random
from typing import Dict, List, Tuple

from .analysis import IndexCompiler, IndexMapper, ParallelMapper
from .board import BoardGenerator
from .graph import GraphGenerator
from .keys import KeyLayout
from .lexer import PrefixRuleFinder, SpecialRuleFinder, StenoLexer

from .rules import RulesDictionary, StenoRule
from .search import IndexSearchDict, TranslationsSearchDict


class StenoEngine:
    """ Main access point for steno analysis. Generates rules from translations and creates visual representations.
        Uses specially created search dictionaries to find translations using a variety of methods. """

    INDEX_DELIM: str = ";"  # Delimiter between rule name and query for index searches.

    def __init__(self, rules:RulesDictionary, board:BoardGenerator, graph:GraphGenerator, lexer:StenoLexer) -> None:
        """ Delegate methods for view-based operations. Add caches to the most expensive and/or frequently called ones.
            Only components with invariant state and methods with immutable output are allowed to have caches. """
        self._rules = rules  # Parses rules from JSON and keeps track of the refs for inverse parsing.
        self._rev_rules = {rules[name]: name for name in rules}
        self._translations = TranslationsSearchDict()
        self._index = IndexSearchDict()
        self.lexer_query = lru_cache()(lexer.query)
        self.lexer_query_uncached = lexer.query
        self.lexer_best_strokes = lexer.best_strokes
        self.graph_generate = lru_cache()(graph.generate)
        self.board_from_keys = lru_cache()(board.from_keys)
        self.board_from_rule = lru_cache()(board.from_rule)

    def set_translations(self, translations:Dict[str,str]) -> None:
        """ Load a new translations search dict. """
        self._translations = TranslationsSearchDict(translations)

    def set_index(self, index:Dict[str,dict]) -> None:
        """ Load a new search index. """
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
        name = self._rev_rules.get(rule)
        return name if name in self._index else ""

    def link_to_rule(self, link:str) -> StenoRule:
        """ Return the rule under the given link name, or None if there is no rule by that name. """
        return self._rules.get(link)

    def make_rules(self, *args, **kwargs) -> Dict[str, list]:
        """ Run the lexer on all translations and return a list of raw rules for saving. """
        mapper = ParallelMapper(self.lexer_query_uncached, **kwargs)
        results = mapper.filtermap(self._translations.items(), *args)
        return self._rules.compile_to_raw(results)

    def make_index(self, *args, match_all_keys=True) -> Dict[str, dict]:
        """ Generate a set of rules from translations using the lexer and compare them to the built-in rules.
            Make a index for each built-in rule containing a dict of every translation that used it.
            Only keep results with all keys matched by default to reduce garbage. """
        mapper = IndexMapper(self.lexer_query_uncached, match_all_keys=match_all_keys)
        results = mapper.sized_filtermap(self._translations.items(), *args)
        return IndexCompiler(self._rev_rules).compile(results)


class StenoResources:
    """ Contains all static resources necessary for a steno system. The structures are mostly JSON dicts.
        Assets including a key layout, rules, and (optional) board graphics comprise the system. """

    def __init__(self, raw_layout:dict, raw_rules:Dict[str,list], board_defs:Dict[str,dict], board_xml:bytes) -> None:
        """ All fields are static steno resources loaded from package assets. """
        self.raw_layout = raw_layout
        self.raw_rules = raw_rules
        self.board_defs = board_defs
        self.board_xml = board_xml

    def build_engine(self) -> StenoEngine:
        """ Load all static resources into steno components and create an engine with them. """
        layout = KeyLayout(self.raw_layout)
        rules = RulesDictionary()
        rules.update_from_raw(self.raw_rules)
        board = BoardGenerator.build(layout, rules, self.board_defs, self.board_xml)
        graph = GraphGenerator(layout)
        sep = layout.SEP
        star = layout.SPECIAL
        special_finder = SpecialRuleFinder(sep, star)
        prefix_finder = PrefixRuleFinder(sep, star)
        lexer = StenoLexer(layout, special_finder, prefix_finder)
        lexer.update(rules)
        return StenoEngine(rules, board, graph, lexer)
