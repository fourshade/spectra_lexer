from functools import lru_cache
import random
from typing import Dict, List, Tuple

from .analysis import IndexInfo, ParallelMapper
from .board import BoardElementParser, BoardEngine
from .graph import StenoGraph
from .keys import KeyLayout
from .lexer import StenoLexer
from .rules import RuleParser, StenoRule
from .search import IndexSearchDict, TranslationsSearchDict


class StenoEngine:
    """ Main access point for steno analysis. Generates rules from translations and creates visual representations.
        Uses specially created search dictionaries to find translations using a variety of methods. """

    INDEX_DELIM: str = ";"  # Delimiter between rule name and query for index searches.

    def __init__(self, rule_parser:RuleParser, board:BoardEngine, lexer:StenoLexer) -> None:
        """ Delegate methods for GUI-based operations. Add caches to the most expensive and/or frequently called ones.
            Only objects with invariant state and methods with immutable output are allowed to have caches. """
        self._rule_parser = rule_parser  # Parses rules from JSON.
        self._board = board
        self._lexer = lexer
        self._translations = TranslationsSearchDict()
        self._index = IndexSearchDict()
        self.board_from_keys = board.from_keys
        self.board_from_rule = lru_cache()(board.from_rule)
        self.graph_generate = lru_cache()(StenoGraph.generate)
        self.lexer_query = lru_cache()(lexer.query)
        self.lexer_best_strokes = lexer.best_strokes

    def set_translations(self, translations:Dict[str, str]) -> None:
        """ Load a new translations search dict. """
        self._translations = TranslationsSearchDict(translations)

    def set_index(self, index:Dict[str, dict]) -> None:
        """ Load a new search index. Make sure it is a dict of dicts and not arbitrary JSON. """
        if type(index) is not dict or not all([type(v) is dict for v in index.values()]):
            raise TypeError("All first-level values in an index must be dicts.")
        self._index = IndexSearchDict(index)

    def search(self, pattern:str, match:str=None, **kwargs) -> List[str]:
        """ Choose an index to use based on delimiters in the input pattern.
            Search for matches in that index. If <match> is given, the search will find mappings instead. """
        *keys, pattern = pattern.split(self.INDEX_DELIM, 1)
        index = self._index if keys else self._translations
        return index.search(*keys, match or pattern, **kwargs)

    def find_example(self, link:str, strokes=False) -> Tuple[str, str]:
        """ Given a rule by name, find one translation using it at random. Return it with the required input text. """
        d = self._index.get(link) or {"": ""}
        k = random.choice(list(d))
        selection = k if strokes else d[k]
        text = self.INDEX_DELIM.join([link, selection])
        return selection, text

    def run(self, keys:str, letters:str, *,
            select_ref:str, find_rule:bool, set_focus:bool, board_ratio:float, match_all_keys:bool,
            recursive_graph:bool, compressed_graph:bool, graph_compat:bool, compound_board:bool):
        """ Run a lexer query and return everything necessary to update the user GUI state. """
        rule = self.lexer_query(keys, letters, match_all_keys=match_all_keys)
        graph = self.graph_generate(rule, recursive=recursive_graph, compressed=compressed_graph, compat=graph_compat)
        text, selected_rule = graph.render(select_ref, find_rule=find_rule, intense=set_focus)
        if selected_rule is None:
            selected_rule = rule
            set_focus = False
        selected_name = selected_rule.name
        link_ref = selected_name if selected_name in self._index else ""
        caption = selected_rule.caption()
        xml = self.board_from_rule(selected_rule, board_ratio, compound=compound_board)
        return text, set_focus, link_ref, caption, xml

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
    """ Contains all static resources necessary for a steno system. The structures are all JSON dicts.
        Assets include a key layout, rules, and board graphics. """

    def __init__(self, raw_layout:dict, raw_rules:Dict[str, list],
                 board_defs:Dict[str, dict], board_elems:Dict[str, dict]) -> None:
        """ All fields are static resources loaded from package assets. """
        self.raw_layout = raw_layout
        self.raw_rules = raw_rules
        self.board_defs = board_defs
        self.board_elems = board_elems

    def build_engine(self) -> StenoEngine:
        """ Load all resources into steno components and create an engine with them. """
        layout = KeyLayout(**self.raw_layout)
        layout.verify()
        rule_sep = StenoRule.separator(layout.SEP)
        rule_parser = RuleParser(self.raw_rules)
        rules = rule_parser.to_list()
        board_parser = BoardElementParser(self.board_defs)
        board_parser.parse(self.board_elems)
        board = board_parser.build_engine(layout)
        lexer = StenoLexer.build(layout, rules, rule_sep)
        return StenoEngine(rule_parser, board, lexer)
