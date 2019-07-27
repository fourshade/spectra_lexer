from itertools import product
from typing import Iterable, List

from .base import LX
from .board import BoardElementParser, BoardGenerator
from .graph import GraphGenerator, StenoGraph
from .lexer import StenoLexer
from spectra_lexer.resource import RulesDictionary, StenoIndex, StenoRule


class StenoAnalyzer(LX):
    """ The primary steno analysis engine. Generates rules from translations and creates visual representations. """

    _board: BoardGenerator = None
    _grapher: GraphGenerator = None
    _lexer: StenoLexer = None

    def Load(self) -> None:
        board_parser = BoardElementParser(self.BOARD_DEFS, self.BOARD_ELEMS)
        self._board = BoardGenerator(self.LAYOUT, self.RULES, board_parser)
        self._grapher = GraphGenerator(self.LAYOUT)
        self._lexer = StenoLexer(self.LAYOUT, self.RULES)

    def LXLexerQuery(self, keys:str, word:str, **kwargs) -> StenoRule:
        return self._lexer.query(keys, word, **kwargs)

    def LXLexerQueryProduct(self, keys:Iterable[str], words:Iterable[str], **kwargs) -> StenoRule:
        return self._lexer.query_best(product(keys, words), **kwargs)

    def LXLexerQueryAll(self, *args, **kwargs) -> RulesDictionary:
        results = self._query_all(*args, **kwargs)
        return self.RULES.compile(results)

    def LXLexerMakeIndex(self, *args) -> StenoIndex:
        """ Only keep results with all keys matched to reduce garbage. """
        filter_in, filter_out = StenoIndex.filters(*args)
        results = self._query_all(filter_in, filter_out, match_all_keys=True)
        return StenoIndex.compile(results, self.RULES.inverse)

    def _query_all(self, *args, **kwargs) -> List[StenoRule]:
        items = self.TRANSLATIONS.items()
        return self._lexer.query_parallel(items, *args, **kwargs)

    def LXGraphGenerate(self, rule:StenoRule, **kwargs) -> StenoGraph:
        return self._grapher(rule, **kwargs)

    def LXBoardFromKeys(self, keys:str, *args) -> bytes:
        return self._board.from_keys(keys, *args)

    def LXBoardFromRule(self, rule:StenoRule, *args) -> bytes:
        return self._board.from_rule(rule, *args)
