from collections import defaultdict, namedtuple
from functools import partial
from itertools import starmap
from multiprocessing import cpu_count, Pool
import sys
from traceback import print_exc
from typing import Callable, Dict, Iterable, List, Tuple

from .lexer import StenoLexer
from .resource import StenoRule


class ParallelMapper:
    """ Class to map functions over large iterables in parallel using multiprocessing.

        Use of multiprocessing is very error-prone due to its requirement to recursively pickle every object associated
        with the provided callable in order to send the entire state to each process. If that callable is a method,
        it must pickle both the instance and the class, which may have many dependencies, all of which must themselves
        be picklable, and so on. Manual pickle handling with __getstate__ and __setstate__ can mitigate this, but some
        objects will never be picklable due to dependence on external resources (i.e. open files). Because of this,
        any time multiprocessing fails, we simply fall back to single-process computation and print a message to stderr.

        Another caveat is that the multiprocessing map operations internally consume the entire iterable to make a list
        before sending the pieces to each process. This means any expensive computations involved in lazy iteration are
        performed *before* any work is done in parallel. However, if we want the possibility of retrying the computation
        with a single process, we have to evaluate the iterable and save the results to a list ourselves anyway. """

    func: Callable
    processes: int

    def __init__(self, func:Callable, *args, processes:int=None, **kwargs):
        """ Extra arguments are treated as partials applying to *every* call. """
        if args or kwargs:
            func = partial(func, *args, **kwargs)
        self.func = func
        # If not specified, the number of processes defaults to the number of CPU cores.
        self.processes = processes or cpu_count() or 1

    def starmap(self, iterable:Iterable[tuple]) -> list:
        """ Equivalent of itertools.starmap using multiprocessing. Returns a list instead of an iterator. """
        if self.processes > 1:
            # Make a list out of the iterable (which may be one-time use) in case we have to retry with one process.
            iterable = list(iterable)
            try:
                # Use Pool.starmap() to call a function on each argument tuple in parallel.
                with Pool(self.processes) as pool:
                    return pool.starmap(self.func, iterable)
            except Exception:
                print_exc()
                print("Parallel operation failed. Trying with a single process...", file=sys.stderr)
        # With only one process (or a failed process pool), use ordinary starmap.
        return list(starmap(self.func, iterable))


class IndexFilters(namedtuple("IndexFilters", "filter_in filter_out")):

    MINIMUM_SIZE = 1   # Minimum index size. Below this size, input filters block everything.
    DEFAULT_SIZE = 12  # Default index size. Essentially the maximum word length.
    MAXIMUM_SIZE = 20  # Maximum index size. At this size and above, input filters are disabled.

    SIZE_DESCRIPTIONS = ["size = 1: includes nothing.",
                         "size = 10: fast index with relatively simple words.",
                         "size = 12: average-sized index (default).",
                         "size = 15: slower index with more advanced words.",
                         "size = 20: includes everything."]

    @classmethod
    def from_size(cls, size:int=DEFAULT_SIZE) -> tuple:
        """ Generate filters to control index size. Larger translations are excluded with smaller index sizes.
            The parameter <size> determines the relative size of a generated index (range 1-20). """
        if size < cls.MINIMUM_SIZE:
            return (lambda t: False, None)
        def filter_in(translation:tuple) -> bool:
            """ Filter function to eliminate larger entries from the index depending on the size factor. """
            return max(map(len, translation)) <= size
        def filter_out(rule:StenoRule) -> bool:
            """ Filter function to eliminate lexer results that are unmatched or basic rules themselves. """
            return len(rule.rulemap) > 1
        return cls(filter_in if size < cls.MAXIMUM_SIZE else None, filter_out)


class StenoAnalyzer:

    _lexer: StenoLexer
    _rules: Dict[str, StenoRule]
    _translations: Iterable[Tuple[str, str]] = ()

    def __init__(self, lexer:StenoLexer, rules:Dict[str, StenoRule]):
        self._lexer = lexer
        self._rules = rules

    def load(self, translations:Iterable) -> None:
        """ Load a set of translations to operate on. """
        self._translations = translations

    def make_rules(self, filter_in=None, filter_out=None, **kwargs) -> List[StenoRule]:
        """ Run the lexer in parallel on all translation items and return a list of results.
            <filter_in> eliminates translations before processing, and <filter_out> eliminates results afterward. """
        mapper = ParallelMapper(self._lexer.query, **kwargs)
        items = self._translations
        if filter_in is not None:
            items = filter(filter_in, items)
        results = mapper.starmap(items)
        if filter_out is not None:
            results = list(filter(filter_out, results))
        return results

    def make_index(self, *args) -> Dict[str, dict]:
        """ Run the lexer in parallel on all translation items and return a translation index.
            Only keep results with all keys matched to reduce garbage. """
        filters = IndexFilters.from_size(*args)
        results = self.make_rules(*filters, match_all_keys=True)
        return self._compile_index(results)

    def _compile_index(self, rules:Iterable[StenoRule]) -> Dict[str, dict]:
        """ Using rulemaps, make dicts of all translations that use each built-in rule at the top level. """
        tr_dicts = defaultdict(dict)
        for rs in rules:
            keys = rs.keys
            letters = rs.letters
            for item in rs.rulemap:
                tr_dicts[item.rule][keys] = letters
        # Convert the rule keys to strings. Hardcoded and missing rules will map to None.
        rev_rules = {v: k for k, v in self._rules.items()}
        d = {rev_rules.get(k): v for k, v in tr_dicts.items()}
        # Entries with no rule are useless, and None/null is not a valid key in JSON, so toss it.
        if None in d:
            del d[None]
        return d
