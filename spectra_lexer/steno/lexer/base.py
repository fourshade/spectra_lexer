from itertools import product
from typing import Callable, Iterable, List, Tuple

from .generate import LexerRuleGenerator
from .match import LexerMatch, LexerRuleMatcher
from .process import LexerProcessor
from ..rules import StenoRule
from ..system import LXSystem
from spectra_lexer.core import COREApp, Component, Signal
from spectra_lexer.system import ConsoleCommand
from spectra_lexer.utils import par_starmap


class LXLexer:

    @ConsoleCommand("lexer_query")
    def query(self, keys:str, word:str, *, need_all_keys:bool=False) -> StenoRule:
        """ Return and send out the best rule that maps the given key string to the given word. """
        raise NotImplementedError

    @ConsoleCommand("lexer_query_product")
    def query_product(self, keys:Iterable[str], words:Iterable[str], *, need_all_keys:bool=False) -> StenoRule:
        """ As arguments, take iterables of keys and words and test every possible pairing.
            Return and send out the best rule out of all combinations. """
        raise NotImplementedError

    @ConsoleCommand("lexer_query_all")
    def query_all(self, items:Iterable[Tuple[str, str]], *, need_all_keys:bool=False) -> List[StenoRule]:
        """ Run the lexer in parallel on all (keys, word) translations in <items> and return a list of results. """
        raise NotImplementedError

    class Output:
        @Signal
        def on_lexer_output(self, rule:StenoRule) -> None:
            raise NotImplementedError

    class OutputList:
        @Signal
        def on_lexer_output_list(self, rules:List[StenoRule]) -> None:
            raise NotImplementedError


class StenoLexer(Component, LXLexer,
                 COREApp.Start, LXSystem.Layout, LXSystem.Rules):
    """ The main lexer engine. Uses trial-and-error stack based analysis to gather all possibilities for steno
        patterns it can find, then sorts among them to find what it considers the most likely to be correct. """

    _matcher: LexerRuleMatcher = None                   # Master rule-matching dictionary.
    _generator: LexerRuleGenerator = None               # Makes rules from lexer matches.
    _cleanse: Callable[[str], str] = staticmethod(str)  # Performs thorough conversions on RTFCRE steno strings.

    def on_app_start(self) -> None:
        layout = self.layout
        match_dict = LexerMatch.convert_dict(self.rules, layout.from_rtfcre)
        self._matcher = LexerRuleMatcher(layout.SEP, layout.SPECIAL, match_dict)
        self._generator = LexerRuleGenerator(layout.to_rtfcre)
        self._cleanse = layout.cleanse_from_rtfcre

    def query(self, keys:str, word:str, **kwargs) -> StenoRule:
        """ Return and send out the best rule that maps the given key string to the given word. """
        return self._output(self._make_processor(**kwargs).query(keys, word))

    def query_product(self, keys:Iterable[str], words:Iterable[str], **kwargs) -> StenoRule:
        """ As arguments, take iterables of keys and words and test every possible pairing.
            Return and send out the best rule out of all combinations. """
        return self._output(self._make_processor(**kwargs).query_best(list(product(keys, words))))

    def _output(self, rule:StenoRule) -> StenoRule:
        self.engine_call(self.Output, rule)
        return rule

    def query_all(self, items:Iterable[Tuple[str, str]], **kwargs) -> List[StenoRule]:
        """ Run the lexer in parallel on all (keys, word) translations in <items> and return a list of results."""
        results = par_starmap(self._make_processor(**kwargs).query, items)
        self.engine_call(self.OutputList, results)
        return results

    def _make_processor(self, *, need_all_keys:bool=False) -> LexerProcessor:
        return LexerProcessor(self._matcher, self._generator, self._cleanse, need_all_keys)
