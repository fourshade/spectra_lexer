from functools import partial
from itertools import starmap
import sys
from typing import Callable, Iterable


class BaseMapper:
    """ Abstract mapper class. Implementations must implement starmap(); map() is derived from it. """

    def map(self, *iterables:Iterable) -> list:
        """ Equivalent of map() using a mapper. Returns a list instead of an iterator. """
        return self.starmap(zip(*iterables))

    def starmap(self, iterable:Iterable[tuple]) -> list:
        """ Equivalent of itertools.starmap() using a mapper. Returns a list instead of an iterator. """
        raise NotImplementedError


class ParallelMapper(BaseMapper):
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

    _func: Callable
    _processes: int

    def __init__(self, func:Callable, *args, processes:int=None, **kwargs) -> None:
        """ If not specified, the number of processes defaults to the number of CPU cores.
            Extra arguments are treated as partials applying to *every* call. """
        if args or kwargs:
            func = partial(func, *args, **kwargs)
        self._func = func
        self._processes = processes

    def starmap(self, iterable:Iterable[tuple]) -> list:
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


class FilterMapper(BaseMapper):
    """ Parallel mapper that filters items from an iterable before and/or after processing. """

    _mapper: BaseMapper
    _filter_in: Callable
    _filter_out: Callable

    def __init__(self, func:Callable, filter_in:Callable=None, filter_out:Callable=None, *args, **kwargs) -> None:
        """ <filter_in> eliminates items before processing, and <filter_out> eliminates results afterward. """
        self._mapper = ParallelMapper(func, *args, **kwargs)
        self._filter_in: Callable = filter_in
        self._filter_out: Callable = filter_out

    def starmap(self, iterable:Iterable[tuple]) -> list:
        """ Run the items through filter_in, then the mapper, then filter_out. Return what's left in a list. """
        if self._filter_in is not None:
            iterable = filter(self._filter_in, iterable)
        results = self._mapper.starmap(iterable)
        if self._filter_out is not None:
            results = list(filter(self._filter_out, results))
        return results
