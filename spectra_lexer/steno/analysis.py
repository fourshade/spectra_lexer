from functools import partial
from itertools import starmap
import os
import sys
from typing import Callable, Iterable, Tuple


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

    def __init__(self, func:Callable, *args, processes=0, retry=True, **kwargs) -> None:
        """ Extra arguments are treated as partials applying to *every* call. """
        if args or kwargs:
            func = partial(func, *args, **kwargs)
        if not processes:
            processes = os.cpu_count() or 1
        self._func = func            # Function to map over.
        self._processes = processes  # Number of parallel processes (0 = one process for each logical CPU core).
        self._retry = retry          # If True, retry with a single process on failure.

    def starmap(self, iterable:Iterable[tuple]) -> list:
        """ Using the saved function, perform the equivalent of itertools.starmap on <iterable> in parallel.
            This will return a list instead of an iterator. No order is guaranteed in the results. """
        # Don't add the overhead of multiprocessing if there's only one process.
        if self._processes == 1:
            return self._serial_starmap(iterable)
        # The iterable may be one-time use. Make a list out of it in case we have to retry with one process.
        iterable = list(iterable)
        try:
            return self._parallel_starmap(iterable)
        except Exception:
            if not self._retry:
                raise
            # If the process pool fails (usually due to pickling problems), retry with ordinary starmap.
            print("Parallel operation failed. Trying with a single process...", file=sys.stderr)
            return self._serial_starmap(iterable)

    def _parallel_starmap(self, iterable:Iterable[tuple]) -> list:
        """ Map the function over <iterable> in parallel with Pool.starmap. """
        # multiprocessing is fairly large, so don't import until we have to.
        from multiprocessing import Pool
        with Pool(processes=self._processes) as pool:
            return pool.starmap(self._func, iterable)

    def _serial_starmap(self, iterable:Iterable[tuple]) -> list:
        """ Map the function over <iterable> with ordinary starmap. """
        return list(starmap(self._func, iterable))


class IndexInfo:
    """ Contains constants regarding index generation. """

    MINIMUM_SIZE = 1   # Minimum index size. Below this size, input filters block everything.
    DEFAULT_SIZE = 12  # Default index size. Essentially the maximum word length.
    MAXIMUM_SIZE = 20  # Maximum index size. At this size and above, input filters are disabled.

    SIZE_DESCRIPTIONS = ["size = 1: includes nothing.",
                         "size = 10: fast index with relatively simple words.",
                         "size = 12: average-sized index (default).",
                         "size = 15: slower index with more advanced words.",
                         "size = 20: includes everything."]

    SIZE_WARNING = "An extremely large index is not necessarily more useful. " \
                   "The index is created from the Plover dictionary, which is very large " \
                   "(about 150,000 translations) with many useless and even erroneous entries. " \
                   "As the index grows, so does the loading time, " \
                   "and past a certain point the garbage will start to crowd out useful information. " \
                   "Unless you are doing batch analysis, there is little benefit to a maximum-sized index."

    def __init__(self, size:int=DEFAULT_SIZE) -> None:
        self._size = size  # Relative index size (1-20).

    def filter_translations(self, translations:Iterable[Tuple[str, str]]) -> Iterable[Tuple[str, str]]:
        """ Filter input translations according to the required index size. """
        size = self._size
        if size < self.MINIMUM_SIZE:
            # If the size is below minimum, it could be a dummy run. Keep nothing.
            return []
        if size >= self.MAXIMUM_SIZE:
            # If the size is maximum, a filter is unnecessary. Keep everything.
            return translations
        # Eliminate long translations before processing depending on the size factor.
        return [t for t in translations if max(map(len, t)) <= size]
