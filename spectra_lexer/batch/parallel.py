from concurrent.futures import ProcessPoolExecutor
from functools import partial
from os import cpu_count

from spectra_lexer import Component


class ParallelExecutor(Component):
    """ Component to run operations in parallel. """

    processes = Option("cmdline", "processes", 0,
                       "Number of processes to run in parallel. Default is one per CPU core.")

    @on("parallel_map")
    def map(self, key:str, *iterables, chunksize:int=None) -> list:
        """ Use ProcessPoolExecutor.map() to call an engine command on each item in <iterables> in parallel.
            The calling thread will block until everything is finished. """
        func = partial(self.engine_call, key)
        # The number of processes defaults to the number of CPU cores.
        processes = self.processes or cpu_count() or 1
        if processes == 1:
            # With only one process, the overhead of a process pool is unnecessary. Use ordinary map().
            return list(map(func, *iterables))
        if chunksize is None:
            # For best performance, split the work up into a single large chunk for each process.
            # Check the sizes of each iterable. If none are sized, use 1 to be safe.
            isizes = [len(i) for i in iterables if hasattr(i, "__len__")] or [1]
            # Divide the smallest size by the process count for the final chunk size (minimum 1).
            chunksize = (min(isizes) // processes) or 1
        # Execute the entire job in parallel and return all results in a list. No order is guaranteed.
        with ProcessPoolExecutor(max_workers=processes) as executor:
            return list(executor.map(func, *iterables, chunksize=chunksize))
