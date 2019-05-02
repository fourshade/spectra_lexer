from itertools import starmap
from multiprocessing import cpu_count, Pool
from traceback import print_exc
from typing import Callable, Iterable

from spectra_lexer import Component


class ParallelExecutor(Component):
    """ Component to run operations in parallel using multiprocessing. """

    processes = resource("cmdline:processes", 0,
                         desc="Number of processes to run in parallel. Default is one per CPU core.")

    @on("parallel_map")
    def map(self, func:Callable, *iterables:Iterable) -> list:
        """ Map a function in parallel over all items in one or more iterables. Order is not guaranteed. """
        return self.starmap(func, zip(*iterables))

    @on("parallel_starmap")
    def starmap(self, func:Callable, iterable:Iterable[tuple]) -> list:
        """ Equivalent of itertools.starmap for a parallel map operation. """
        # The number of processes defaults to the number of CPU cores.
        processes = self.processes or cpu_count() or 1
        # To avoid consuming the iterable, it must be a list. multiprocessing internally makes a list from it anyway.
        args_list = list(iterable)
        if processes > 1:
            try:
                # Use Pool.starmap() to call a function on each argument tuple in <iterable> in parallel.
                with Pool(processes) as pool:
                    return pool.starmap(func, args_list)
            except Exception:
                print_exc()
                print("Parallel operation failed. Trying with a single process...")
        # With only one process (or a failed process pool), use ordinary starmap.
        return list(starmap(func, args_list))
