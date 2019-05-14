from collections import defaultdict
from typing import Callable, Iterable, List

from .index import StenoIndex
from .lexer import LXLexer
from .rules import StenoRule
from .system import LXSystem
from .translations import LXTranslations
from spectra_lexer.core import COREApp, Component, Signal
from spectra_lexer.system import ConsoleCommand, SYSControl

# Default size of generated indices (maximum word size).
_DEFAULT_INDEX_SIZE = 12


class LXAnalyzer:

    @ConsoleCommand("analyzer_make_rules")
    def make_rules(self, filter_in:Callable=None, filter_out:Callable=None, **kwargs) -> List[StenoRule]:
        """ Run the lexer on all currently loaded translations. Show status messages on start and finish. """
        raise NotImplementedError

    @ConsoleCommand("analyzer_make_index")
    def make_index(self, size:int) -> StenoIndex:
        """ Generate a set of rules from translations using the lexer and compare them to the built-in rules.
            Make a index for each built-in rule containing a dict of every translation that used it. """
        raise NotImplementedError

    class Ready:
        @Signal
        def on_analyzer_ready(self) -> None:
            raise NotImplementedError

    class Start:
        @Signal
        def on_analyzer_start(self) -> None:
            raise NotImplementedError

    class Finish:
        @Signal
        def on_analyzer_finish(self) -> None:
            raise NotImplementedError

    class NewRules:
        @Signal
        def on_new_analyzer_rules(self, rules:List[StenoRule]) -> None:
            raise NotImplementedError

    class NewIndex:
        @Signal
        def on_new_analyzer_index(self, d:StenoIndex) -> None:
            raise NotImplementedError


class StenoAnalyzer(Component, LXAnalyzer,
                    LXSystem.Rules, LXTranslations.Dict,
                    COREApp.Start):
    """ The primary batch steno analysis engine. Queries the lexer in bulk and creates indices. """

    def on_app_start(self) -> None:
        """ When the analyzer's resources are ready, send a signal to tell other threads that everything's usable. """
        self.engine_call(self.Ready)

    def _start(self, msg:str) -> None:
        """ Start an analysis task and send a signal (since it might take a while). """
        self.engine_call(self.Start)
        self.engine_call(SYSControl.status, msg)

    def _finish(self, msg:str) -> None:
        """ Send a signal that we're finished with analysis and are no longer hogging the thread. """
        self.engine_call(SYSControl.status, msg)
        self.engine_call(self.Finish)

    def make_rules(self, *args, **kwargs) -> List[StenoRule]:
        """ Run the lexer on all currently loaded translations. Show status messages on start and finish. """
        self._start("Analyzing translations...")
        results = self._filtered_query_all(*args, **kwargs)
        self.engine_call(self.NewRules, results)
        self._finish("Analysis complete!")
        return results

    def make_index(self, size:int=_DEFAULT_INDEX_SIZE) -> StenoIndex:
        """ Generate a set of rules from translations using the lexer and compare them to the built-in rules.
            Make a index for each built-in rule containing a dict of every translation that used it. """
        self._start("Making new index...")
        filter_in, filter_out = self._make_index_filters(size)
        # Only keep results with all keys matched to reduce garbage.
        results = self._filtered_query_all(filter_in, filter_out, need_all_keys=True)
        d = self._compile_index(results)
        self.engine_call(self.NewIndex, d)
        self._finish("Successfully created index!")
        return d

    def _filtered_query_all(self, filter_in:Callable=None, filter_out:Callable=None, **kwargs) -> List[StenoRule]:
        """ Run the lexer in parallel on all currently loaded translations and return a list of results.
            <filter_in> eliminates translations before processing, and <filter_out> eliminates results afterward. """
        items = self.translations.items()
        if filter_in is not None:
            items = filter(filter_in, items)
        results = self.engine_call(LXLexer.query_all, items, **kwargs)
        if filter_out is not None:
            results = list(filter(filter_out, results))
        return results

    def _make_index_filters(self, size:int) -> tuple:
        """ Generate filters to control index size. Larger words are excluded with smaller index sizes.
            The parameter <size> determines the relative size of a generated index (range 1-20). """
        def filter_in(translation:tuple, max_length:int=size) -> bool:
            """ Filter function to eliminate larger entries from the index depending on the size factor. """
            return max(map(len, translation)) <= max_length
        def filter_out(rule:StenoRule) -> bool:
            """ Filter function to eliminate lexer results that are unmatched or basic rules themselves. """
            return len(rule.rulemap) > 1
        return (filter_in if size < 20 else None), filter_out

    def _compile_index(self, results:Iterable[StenoRule]) -> StenoIndex:
        """ From lexer rulemaps, make dicts of all translations that use each built-in rule at the top level. """
        tr_dicts = defaultdict(dict)
        for rs in results:
            keys = rs.keys
            letters = rs.letters
            for item in rs.rulemap:
                tr_dicts[item.rule][keys] = letters
        # Convert the rule keys to strings. Hardcoded and missing rules will map to None.
        rev_rules = self.rules.inverted()
        index = StenoIndex({rev_rules.get(k): v for k, v in tr_dicts.items()})
        # Entries with no rule are useless, and None/null is not a valid key in JSON, so toss it.
        if None in index:
            del index[None]
        return index
