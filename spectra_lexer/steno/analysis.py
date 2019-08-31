from collections import defaultdict
from functools import partial
from itertools import starmap
import sys
from typing import Callable, Dict, Iterable

from .rules import StenoRule


class ParallelMapper:
    """ Maps functions over large iterables in parallel using multiprocessing.

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

    def __init__(self, func:Callable, *args, processes:int=None, **kwargs) -> None:
        """ Extra arguments are treated as partials applying to *every* call. """
        if args or kwargs:
            func = partial(func, *args, **kwargs)
        self._func = func            # Function to map over.
        self._processes = processes  # If not specified, the number of processes defaults to the number of CPU cores.

    def map(self, *iterables:Iterable) -> list:
        """ Equivalent of map() using a mapper. Returns a list instead of an iterator. """
        return self.starmap(zip(*iterables))

    def starmap(self, iterable:Iterable[tuple]) -> list:
        """ Equivalent of itertools.starmap() using a mapper. Returns a list instead of an iterator. """
        # Make a list out of the iterable (which may be one-time use) in case we have to retry with one process.
        iterable = list(iterable)
        try:
            # multiprocessing is fairly large, so don't import until we have to.
            from multiprocessing import Pool
            with Pool(processes=self._processes) as pool:
                return pool.starmap(self._func, iterable)
        except Exception:
            # If the process pool failed (usually due to pickling problems), use ordinary starmap.
            print("Parallel operation failed. Trying with a single process...", file=sys.stderr)
            return list(starmap(self._func, iterable))

    def filtermap(self, iterable:Iterable[tuple], filter_in:Callable=None, filter_out:Callable=None) -> list:
        """ <filter_in> eliminates items before processing, and <filter_out> eliminates results afterward.
            Run the items through filter_in, then the mapper, then filter_out. Return what's left in a list. """
        if filter_in is not None:
            iterable = filter(filter_in, iterable)
        results = self.starmap(iterable)
        if filter_out is not None:
            results = list(filter(filter_out, results))
        return results


class IndexMapper(ParallelMapper):
    """ Filter mapper with basic integer size control for index creation. """

    MINIMUM_SIZE = 1   # Minimum index size. Below this size, input filters block everything.
    DEFAULT_SIZE = 12  # Default index size. Essentially the maximum word length.
    MAXIMUM_SIZE = 20  # Maximum index size. At this size and above, input filters are disabled.

    SIZE_DESCRIPTIONS = ["size = 1: includes nothing.",
                         "size = 10: fast index with relatively simple words.",
                         "size = 12: average-sized index (default).",
                         "size = 15: slower index with more advanced words.",
                         "size = 20: includes everything."]

    def sized_filtermap(self, iterable:Iterable[tuple], size:int=DEFAULT_SIZE) -> list:
        """ Generate filters to control index size. Larger translations are excluded with smaller index sizes. """
        if size < self.MINIMUM_SIZE:
            # If the size is below minimum, it could be a dummy run. Don't run an analysis; just return an empty list.
            return []
        def filter_in(translation:tuple) -> bool:
            """ Filter function to eliminate larger entries from the index depending on the size factor. """
            return max(map(len, translation)) <= size
        if size >= self.MAXIMUM_SIZE:
            # Remove the overhead of the input filter if we're keeping everything.
            filter_in = None
        def filter_out(rule:StenoRule) -> bool:
            """ Filter function to eliminate lexer results that are unmatched or basic rules themselves. """
            return len(rule.rulemap) > 1
        return self.filtermap(iterable, filter_in, filter_out)


class IndexCompiler:
    """ Turns lists of lexer-generated steno rules into dictionaries. """

    def __init__(self, rev_rules:Dict[StenoRule, str]) -> None:
        self._rev_rules = rev_rules  # Reverse dict of built-in rules.

    def compile(self, results:Iterable[StenoRule]) -> Dict[str, dict]:
        """ Using rulemaps, make dicts of all translations that use each built-in rule at the top level. """
        tr_dicts = defaultdict(dict)
        for rs in results:
            keys = rs.keys
            letters = rs.letters
            for item in rs.rulemap:
                tr_dicts[item.rule][keys] = letters
        # Convert the rule keys to strings. Hardcoded and missing rules will map to None.
        d = {self._rev_rules.get(k): v for k, v in tr_dicts.items()}
        # Entries with no rule are useless, and None/null is not a valid key in JSON, so toss it.
        if None in d:
            del d[None]
        return d
