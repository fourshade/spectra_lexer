from concurrent.futures import ProcessPoolExecutor
from functools import partial
from os import cpu_count
from traceback import print_exc
from typing import Iterable

from spectra_lexer import Component


class ParallelExecutor(Component):
    """ Component to run operations in parallel. """

    processes = Option("cmdline", "processes", 0,
                       "Number of processes to run in parallel. Default is one per CPU core.")

    @on("parallel_map")
    def map(self, key:str, *iterables:Iterable) -> list:
        """ Map an engine command in parallel over all items in one or more iterables. Order is not guaranteed.
            If the parallel component fails or is not loaded, do it using a regular map function instead.
            Parallel ops are typically all-or-nothing, so consumable iterators should be safe to retry on failure. """
        try:
            # The number of processes defaults to the number of CPU cores.
            self.processes = self.processes or cpu_count() or 1
            self._compute_chunksize(*iterables)
            results = self._execute(key, *iterables, chunksize=self._compute_chunksize(*iterables))
        except Exception:
            results = None
            print_exc()
        if results is None:
            print("Parallel operation failed. Trying with a single process...")
            results = list(map(partial(self.engine_call, key), *iterables))
        return results

    @on("parallel_starmap")
    def starmap(self, key:str, iterable:Iterable) -> list:
        """ Equivalent of itertools.starmap() for an engine command. """
        return self.map(key, *zip(*iterable))

    def _compute_chunksize(self, *iterables:Iterable) -> int:
        """ For best performance, split the work up into a single large chunk for each process. """
        # Check the sizes of each iterable. If none are sized, use 1 to be safe.
        isizes = [len(i) for i in iterables if hasattr(i, "__len__")] or [1]
        # Divide the smallest size by the process count for the final chunk size (minimum 1).
        chunksize = (min(isizes) // self.processes) or 1
        return chunksize

    def _execute(self, key:str, *iterables:Iterable, **kwargs) -> list:
        """ Use ProcessPoolExecutor.map() to call an engine command on each item in <iterables> in parallel.
            The calling thread will block until everything is finished. No order is guaranteed. """
        func = partial(self.engine_call, key)
        if self.processes == 1:
            # With only one process, the overhead of a process pool is unnecessary. Use ordinary map().
            return list(map(func, *iterables))
        with ProcessPoolExecutor(max_workers=self.processes) as executor:
            return list(executor.map(func, *iterables, **kwargs))
