from functools import partial
from itertools import starmap
import os
import sys
from typing import Callable, ItemsView, Iterable, Union


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

    _STARMAP_ITERABLE = Union[Iterable[tuple], ItemsView]  # Union of all types that work with starmap.

    def __init__(self, func:Callable, *args, processes=0, retry=True, **kwargs) -> None:
        """ Extra arguments are treated as partials applying to *every* call. """
        if args or kwargs:
            func = partial(func, *args, **kwargs)
        if not processes:
            processes = os.cpu_count() or 1
        self._func = func            # Function to map over.
        self._processes = processes  # Number of parallel processes (0 = one process for each logical CPU core).
        self._retry = retry          # If True, retry with a single process on failure.

    def map(self, *iterables:Iterable) -> list:
        """ Using the saved function, perform the equivalent of builtins.map on <iterables> in parallel. """
        return self.starmap(zip(*iterables))

    def starmap(self, iterable:_STARMAP_ITERABLE) -> list:
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

    def _parallel_starmap(self, iterable:_STARMAP_ITERABLE) -> list:
        """ Map the function over <iterable> in parallel with Pool.starmap. """
        # multiprocessing is fairly large, so don't import until we have to.
        from multiprocessing import Pool
        with Pool(processes=self._processes) as pool:
            return pool.starmap(self._func, iterable)

    def _serial_starmap(self, iterable:_STARMAP_ITERABLE) -> list:
        """ Map the function over <iterable> with ordinary starmap. """
        return list(starmap(self._func, iterable))
