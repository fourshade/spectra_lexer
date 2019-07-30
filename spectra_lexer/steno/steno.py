from itertools import product
from typing import Iterable, List

from .base import LX
from .board import BoardElementParser, BoardGenerator
from .graph import GraphGenerator, StenoGraph
from .lexer import StenoLexer
from spectra_lexer.resource import KeyLayout, RS, RulesDictionary, StenoIndex, StenoRule, TranslationsDictionary
from spectra_lexer.codec import XMLElement


class StenoAnalyzer(RS, LX):
    """ The primary steno analysis engine. Generates rules from translations and creates visual representations. """

    _board: BoardGenerator = None
    _grapher: GraphGenerator = None
    _lexer: StenoLexer = None
    _rules: RulesDictionary = None
    _translations: TranslationsDictionary = None

    def RSSystemReady(self, layout:KeyLayout, rules:RulesDictionary, board_defs:dict, board_elems:XMLElement) -> None:
        self._board = BoardGenerator(layout, rules, board_defs, board_elems)
        self._grapher = GraphGenerator(layout)
        self._lexer = StenoLexer(layout, rules)
        self._rules = rules

    def RSTranslationsReady(self, translations:TranslationsDictionary) -> None:
        self._translations = translations

    def LXLexerQuery(self, keys:str, word:str, **kwargs) -> StenoRule:
        return self._lexer.query(keys, word, **kwargs)

    def LXLexerQueryProduct(self, keys:Iterable[str], words:Iterable[str], **kwargs) -> StenoRule:
        return self._lexer.query_best(product(keys, words), **kwargs)

    def LXLexerQueryAll(self, *args, **kwargs) -> RulesDictionary:
        results = self._query_all(*args, **kwargs)
        return self._rules.compile(results)

    def LXLexerMakeIndex(self, *args) -> StenoIndex:
        """ Only keep results with all keys matched to reduce garbage. """
        filter_in, filter_out = StenoIndex.filters(*args)
        results = self._query_all(filter_in, filter_out, match_all_keys=True)
        return StenoIndex.compile(results, self._rules.inverse)

    def _query_all(self, *args, **kwargs) -> List[StenoRule]:
        items = self._translations.items()
        return self._lexer.query_parallel(items, *args, **kwargs)

    def LXGraphGenerate(self, rule:StenoRule, **kwargs) -> StenoGraph:
        return self._grapher(rule, **kwargs)

    def LXBoardFromKeys(self, keys:str, *args) -> bytes:
        return self._board.from_keys(keys, *args)

    def LXBoardFromRule(self, rule:StenoRule, *args) -> bytes:
        return self._board.from_rule(rule, *args)
