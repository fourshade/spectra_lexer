from concurrent.futures import ProcessPoolExecutor
from os import cpu_count

from spectra_lexer import Component, respond_to
from spectra_lexer.options import CommandOption


class ParallelExecutor(Component):
    """ Component to run operations in parallel. """

    ROLE = "parallel"
    processes: int = CommandOption(None, "Number of processes to run at once (if None, use one for each CPU core).")

    @respond_to("parallel_map")
    def map(self, func:callable, *iterables, chunksize:int=None) -> list:
        """ Use ProcessPoolExecutor.map() to run an operation in multiple processes in parallel. """
        # The number of processes defaults to the number of CPU cores.
        processes = self.processes or cpu_count() or 1
        if chunksize is None:
            # For best performance, split the work up into a single large chunk for each process.
            # Check the sizes of each iterable. If none are sized, use 1 to be safe.
            isizes = [len(i) for i in iterables if hasattr(i, "__len__")] or [1]
            # Divide the smallest size by the process count for the final chunk size (minimum 1).
            chunksize = (min(isizes) // processes) or 1
        with ProcessPoolExecutor(max_workers=processes) as executor:
            return list(executor.map(func, *iterables, chunksize=chunksize))
