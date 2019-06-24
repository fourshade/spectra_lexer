from itertools import product
from typing import Callable, Iterable

from .generate import LexerRuleGenerator
from .match import LexerMatch, LexerRuleMatcher
from .process import LexerProcessor
from ..base import LX
from spectra_lexer.resource import RulesDictionary, StenoIndex, StenoRule


class StenoLexer(LX):
    """ The primary steno analysis engine. Generates rules from translations and creates indices. """

    _DEFAULT_INDEX_SIZE: int = 12  # Default size of generated indices (maximum word size).

    _matcher: LexerRuleMatcher = None      # Master rule-matching dictionary.
    _generator: LexerRuleGenerator = None  # Makes rules from lexer matches.
    _cleanse: Callable[[str], str] = None  # Performs thorough conversions on RTFCRE steno strings.

    def Load(self) -> None:
        layout = self.LAYOUT
        match_dict = LexerMatch.convert_dict(self.RULES, layout.from_rtfcre)
        self._matcher = LexerRuleMatcher(layout.SEP, layout.SPECIAL, match_dict)
        self._generator = LexerRuleGenerator(layout.to_rtfcre)
        self._cleanse = layout.cleanse_from_rtfcre

    def LXLexerQuery(self, keys:str, word:str, **kwargs) -> StenoRule:
        return self._make_processor(**kwargs).query(keys, word)

    def LXLexerQueryProduct(self, keys:Iterable[str], words:Iterable[str], **kwargs) -> StenoRule:
        return self._make_processor(**kwargs).query_best(product(keys, words))

    def LXLexerQueryAll(self, *args, **kwargs) -> RulesDictionary:
        results = self._query_all(*args, **kwargs)
        return RulesDictionary(zip(map(str, results), results), **self.RULES)

    def LXLexerMakeIndex(self, size:int=_DEFAULT_INDEX_SIZE) -> StenoIndex:
        """ Only keep results with all keys matched to reduce garbage. """
        filter_in, filter_out = StenoIndex.filters(size)
        results = self._query_all(filter_in, filter_out, need_all_keys=True)
        return StenoIndex.compile(results, self.RULES.inverse)

    def _query_all(self, *args, **kwargs):
        items = self.TRANSLATIONS.items()
        return self._make_processor(**kwargs).query_parallel(items, *args)

    def _make_processor(self, *, need_all_keys:bool=False) -> LexerProcessor:
        return LexerProcessor(self._matcher, self._generator, self._cleanse, need_all_keys)
