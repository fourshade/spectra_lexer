from itertools import product
from typing import Dict, Iterable, List, Tuple

from .analyzer import StenoAnalyzer
from .base import LX
from .board import BoardGenerator
from .graph import GraphGenerator, StenoGraph
from .lexer import StenoLexer
from .search import SearchEngine
from spectra_lexer.resource import KeyLayout, RS, StenoRule, XMLElement


class StenoEngine(RS, LX):
    """ The primary steno analysis engine. Generates rules from translations and creates visual representations. """

    _board: BoardGenerator = None
    _grapher: GraphGenerator = None
    _lexer: StenoLexer = None
    _analyzer: StenoAnalyzer = None
    _search: SearchEngine = None

    def RSSystemReady(self, layout:KeyLayout, rules:Dict[str, StenoRule],
                      board_defs:dict, board_elems:XMLElement) -> None:
        self._board = BoardGenerator(layout, rules, board_defs, board_elems)
        self._grapher = GraphGenerator(layout)
        self._lexer = StenoLexer(layout, rules)
        self._analyzer = StenoAnalyzer(self._lexer, rules)
        self._search = SearchEngine(rules)

    def RSTranslationsReady(self, translations:Dict[str, str]) -> None:
        self._search.load_translations(translations)
        self._analyzer.load(translations.items())

    def RSIndexReady(self, index:Dict[str, dict]) -> None:
        self._search.load_index(index)

    def LXLexerQuery(self, keys:str, word:str, **kwargs) -> StenoRule:
        return self._lexer.query(keys, word, **kwargs)

    def LXLexerQueryProduct(self, keys:Iterable[str], words:Iterable[str], **kwargs) -> StenoRule:
        return self._lexer.query_best(product(keys, words), **kwargs)

    def LXAnalyzerMakeRules(self, *args, **kwargs) -> List[StenoRule]:
        return self._analyzer.make_rules(*args, **kwargs)

    def LXAnalyzerMakeIndex(self, *args) -> Dict[str, dict]:
        return self._analyzer.make_index(*args)

    def LXGraphGenerate(self, rule:StenoRule, **kwargs) -> StenoGraph:
        return self._grapher(rule, **kwargs)

    def LXBoardFromKeys(self, keys:str, *args) -> bytes:
        return self._board.from_keys(keys, *args)

    def LXBoardFromRule(self, rule:StenoRule, *args) -> bytes:
        return self._board.from_rule(rule, *args)

    def LXSearchQuery(self, *args, **kwargs) -> List[str]:
        return self._search.search(*args, **kwargs)

    def LXSearchFindExample(self, *args, **kwargs) -> Tuple[str, str]:
        return self._search.find_example(*args, **kwargs)

    def LXSearchFindLink(self, rule:StenoRule) -> str:
        return self._search.rule_to_link(rule)

    def LXSearchFindRule(self, link:str) -> StenoRule:
        return self._search.link_to_rule(link)
