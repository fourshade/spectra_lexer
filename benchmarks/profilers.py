""" Various profilers for Python callables. """

from cProfile import Profile
from io import StringIO
import pstats
import time


class AbstractProfiler:
    """ Abstract tool to measure and format details about the execution of a Python callable. """

    def run(self, func, *args) -> None:
        """ Evaluate a function under a timer and record details about its performance. """
        raise NotImplementedError

    def format_best(self) -> str:
        """ Format a string with the details about the quickest recorded run. """
        raise NotImplementedError


class RawProfiler(AbstractProfiler):
    """ Records a function's total execution time only. """

    def __init__(self) -> None:
        self._times = []  # Time in seconds for each call to run().

    def run(self, func, *args) -> None:
        """ Evaluate a function under a simple timer. """
        start_time = time.time()
        func(*args)
        self._times.append(time.time() - start_time)

    def format_best(self) -> str:
        """ Format a string with the execution time of the quickest run. """
        return f'Total time = {min(self._times):.3f}s\n'


class DetailedProfiler(AbstractProfiler):
    """ Records execution time for each method call that recursively composes a top-level function.
        For code with lots of tiny methods, profiling overhead may be substantial. """

    def __init__(self, *, max_lines=50, strip_to_level=2) -> None:
        self._stats = []                       # Statistics for each call to run().
        self._max_lines = max_lines            # Maximum number of methods to print profiles on.
        self._strip_to_level = strip_to_level  # Limit (if any) on directory levels shown in file listing.

    def run(self, func, *args) -> None:
        """ Evaluate a function using cProfile.Profile. """
        pr = Profile()
        pr.enable()
        func(*args)
        pr.disable()
        pr.create_stats()
        self._stats.append(pr)

    def format_best(self) -> str:
        """ Format a string with the execution time for each method during the quickest run. """
        colwidths = [12, 7, None, 7, None]
        colsep = "   "
        best_pr = min(self._stats, key=lambda p: max(s[3] for s in p.stats.values()))
        s_buf = StringIO()
        ps = pstats.Stats(best_pr, stream=s_buf).sort_stats('cumulative')
        ps.print_stats(self._max_lines)
        stats = s_buf.getvalue()
        sections = []
        for line in stats.splitlines()[4:]:
            if line.strip():
                *fields, path = line.split(maxsplit=5)
                if self._strip_to_level:
                    for sep in ('\\', '/'):
                        if sep in path:
                            segments = path.rsplit(sep, self._strip_to_level)
                            path = sep.join(segments[1:])
                            break
                for f, w in zip(fields, colwidths):
                    if w is not None:
                        sections += [f.rjust(w), colsep]
                sections += [path, '\n']
        return ''.join(sections)
