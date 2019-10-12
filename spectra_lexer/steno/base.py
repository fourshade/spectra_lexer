import random
from typing import Dict, List, Tuple

from .analysis import IndexInfo, ParallelMapper
from .board import BoardElementParser, BoardEngine
from .graph import GraphEngine
from .keys import KeyLayout
from .lexer import LexerFactory, StenoLexer
from .rules import RuleParser, StenoRule
from .search import IndexSearchDict, TranslationsSearchDict


class StenoEngine:
    """ Main access point for steno analysis. Generates rules from translations and creates visual representations.
        Uses specially created search dictionaries to find translations using a variety of methods. """

    INDEX_DELIM: str = ";"  # Delimiter between rule name and query for index searches.

    def __init__(self, rule_parser:RuleParser, lexer:StenoLexer,
                 board_engine:BoardEngine, graph_engine:GraphEngine) -> None:
        self._rule_parser = rule_parser  # Parses rules from JSON.
        self._lexer = lexer
        self._board_engine = board_engine
        self._graph_engine = graph_engine
        self._translations = TranslationsSearchDict()
        self._index = IndexSearchDict()
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
            graph_compress:bool, graph_compat:bool, board_compound:bool):
        """ Run a lexer query and return everything necessary to update the user GUI state. """
        rule = self.lexer_query(keys, letters, match_all_keys=match_all_keys)
        graph = self._graph_engine.generate(rule, compressed=graph_compress, compat=graph_compat)
        if find_rule:
            node = graph.find_node_from_rule_name(select_ref)
        else:
            node = graph.find_node_from_ref(select_ref)
        text = graph.render(node, intense=set_focus)
        link_ref = ""
        if node is not None:
            selected_rule_name = node.rule_name()
            if selected_rule_name in self._index:
                link_ref = selected_rule_name
        else:
            selected_rule_name = ""
            set_focus = False
        board_rule = self._rule_parser.get(selected_rule_name) or rule
        caption = board_rule.caption()
        xml = self._board_engine.from_rule(board_rule, board_ratio, compound=board_compound)
        return text, set_focus, link_ref, caption, xml

    def lexer_query(self, *args, **kwargs) -> StenoRule:
        return self._lexer.query(*args, **kwargs)

    def make_rules(self, **kwargs) -> Dict[str, list]:
        """ Run the lexer on all translations and return a list of raw rules for saving. """
        mapper = ParallelMapper(self._lexer.query, **kwargs)
        results = mapper.starmap(self._translations.items())
        return self._rule_parser.compile_to_raw(results)

    def make_index(self, size:int, match_all_keys=True, **kwargs) -> Dict[str, dict]:
        """ Make a index from a parallel lexer query operation. Use an input filter to control size.
            Only keep results with all keys matched by default to reduce garbage. """
        info = IndexInfo(size)
        mapper = ParallelMapper(self._lexer.query, match_all_keys=match_all_keys, **kwargs)
        translations_in = info.filter_translations(self._translations.items())
        results = mapper.starmap(translations_in)
        return self._rule_parser.compile_tr_index(results)


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
        rule_parser = RuleParser(self.raw_rules)
        rules = rule_parser.to_list()
        lexer_factory = LexerFactory(layout)
        for rule in rules:
            lexer_factory.add(rule)
        rule_sep = StenoRule.separator(layout.sep)
        lexer = lexer_factory.build_lexer(rule_sep)
        board_parser = BoardElementParser(self.board_defs)
        board_parser.parse(self.board_elems)
        board_engine = board_parser.build_engine(layout)
        graph_engine = GraphEngine()
        return StenoEngine(rule_parser, lexer, board_engine, graph_engine)
