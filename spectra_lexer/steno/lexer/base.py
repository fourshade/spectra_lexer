from itertools import product
from typing import Iterable

from .generate import LexerRuleGenerator
from .match import LexerMatch, LexerRuleMatcher
from .process import LexerProcessor
from ..base import LX
from spectra_lexer.resource import RulesDictionary, StenoIndex, StenoRule


class StenoLexer(LX):
    """ The primary steno analysis engine. Generates rules from translations and creates indices. """

    _processor: LexerProcessor = None

    def Load(self) -> None:
        layout = self.LAYOUT
        match_dict = LexerMatch.convert_dict(self.RULES, layout.from_rtfcre)
        matcher = LexerRuleMatcher(layout.SEP, layout.SPECIAL, match_dict)
        generator = LexerRuleGenerator(layout.to_rtfcre)
        self._processor = LexerProcessor(matcher, generator, layout.cleanse_from_rtfcre)

    def LXLexerQuery(self, keys:str, word:str, **kwargs) -> StenoRule:
        return self._processor.query(keys, word, **kwargs)

    def LXLexerQueryProduct(self, keys:Iterable[str], words:Iterable[str], **kwargs) -> StenoRule:
        return self._processor.query_best(product(keys, words), **kwargs)

    def LXLexerQueryAll(self, *args, **kwargs) -> RulesDictionary:
        results = self._query_all(*args, **kwargs)
        return RulesDictionary(zip(map(str, results), results), **self.RULES)

    def LXLexerMakeIndex(self, *args) -> StenoIndex:
        """ Only keep results with all keys matched to reduce garbage. """
        filter_in, filter_out = StenoIndex.filters(*args)
        results = self._query_all(filter_in, filter_out, need_all_keys=True)
        return StenoIndex.compile(results, self.RULES.inverse)

    def _query_all(self, *args, **kwargs):
        items = self.TRANSLATIONS.items()
        return self._processor.query_parallel(items, *args, **kwargs)
