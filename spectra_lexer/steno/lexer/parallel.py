from functools import partial
from itertools import starmap
from multiprocessing import cpu_count, Pool
import sys
from traceback import print_exc
from typing import Callable, Iterable


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
