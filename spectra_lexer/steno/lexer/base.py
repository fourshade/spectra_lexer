from itertools import product
from typing import Callable, Iterable, List

from .generate import LexerRuleGenerator
from .match import LexerMatch, LexerRuleMatcher
from .process import LexerProcessor
from ..base import LX
from spectra_lexer.resource import StenoRule
from spectra_lexer.utils import par_starmap


class StenoLexer(LX):
    """ The main lexer engine. Uses trial-and-error stack based analysis to gather all possibilities for steno
        patterns it can find, then sorts among them to find what it considers the most likely to be correct. """

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
        return self._make_processor(**kwargs).query_best(list(product(keys, words)))

    def LXQueryAll(self, filter_in:Callable=None, filter_out:Callable=None, **kwargs) -> List[StenoRule]:
        items = self.TRANSLATIONS.items()
        if filter_in is not None:
            items = filter(filter_in, items)
        results = par_starmap(self._make_processor(**kwargs).query, items)
        if filter_out is not None:
            results = list(filter(filter_out, results))
        return results

    def _make_processor(self, *, need_all_keys:bool=False) -> LexerProcessor:
        return LexerProcessor(self._matcher, self._generator, self._cleanse, need_all_keys)
