#!/usr/bin/env python3

from cProfile import Profile
from io import StringIO
from pstats import Stats
from time import time


class BaseTestRunner:
    """ Measures and prints the execution time for a given function with given test arguments. """

    def __init__(self, func, setup=lambda: None) -> None:
        self._func = func    # Function to profile
        self._setup = setup  # Optional function to call before each simulation. """
        self._stats = []

    def run(self, test_data) -> None:
        """ Evaluate a function under a timer.
            <test_data> - Iterable of tuples containing positional test arguments, one tuple per test. """
        self._setup()
        timer = self._on()
        func = self._func
        for t in test_data:
            func(*t)
        self._off(timer)

    def _on(self):
        raise NotImplementedError

    def _off(self, timer) -> None:
        raise NotImplementedError

    def format_best(self, **kwargs) -> str:
        raise NotImplementedError


class RawTestRunner(BaseTestRunner):

    def _on(self) -> float:
        return time()

    def _off(self, start_time:float) -> None:
        self._stats.append(time() - start_time)

    def format_best(self, **kwargs) -> str:
        return f"raw time = {min(self._stats):.3f}s\n"


class ProfileTestRunner(BaseTestRunner):

    def _on(self) -> Profile:
        pr = Profile()
        pr.enable()
        return pr

    def _off(self, pr:Profile) -> None:
        pr.disable()
        pr.create_stats()
        self._stats.append(pr)

    def format_best(self, *, max_lines=50, strip_to_level=1, **kwargs) -> str:
        """ Format a string with the execution time for each method during the quickest run.
        <max_lines> - maximum number of methods to print profiles on.
        <param strip_to_level> - how many directory levels do we leave in each file listing?
                                 None: C:\\ProgramData\\Anaconda3\\lib\\test.py
                                 0: test.py
                                 1: lib\\test.py """
        colwidths = [12, 7, None, 7, None]
        colsep = "   "
        best_pr = min(self._stats, key=lambda p: max(s[3] for s in p.stats.values()))
        s_buf = StringIO()
        ps = Stats(best_pr, stream=s_buf).sort_stats('cumulative')
        ps.print_stats(max_lines)
        sections = ["Benchmark for ", self._func.__qualname__ , ", best of ", str(len(self._stats)), ":\n\n"]
        for line in s_buf.getvalue().splitlines()[5:]:
            if line.strip():
                *fields, path = line.split(maxsplit=5)
                if strip_to_level is not None:
                    path_segments = path.split('\\')
                    stripped_segments = path_segments[-strip_to_level-1:]
                    path = "\\".join(stripped_segments)
                for f, w in zip(fields, colwidths):
                    if w is not None:
                        sections += [f.rjust(w), colsep]
                sections += [path, '\n']
        return "".join(sections)


class MultiProfiler:
    """ Runs benchmarks using multiple test runners on the same function and data. """

    def __init__(self, *runner_types) -> None:
        self._runner_types = runner_types

    def run(self, func, args_iter=((),), *args, best_of=1, **kwargs) -> None:
        """ Measure and print the execution time for <func> to evaluate all of the argument sets in <args_iter>.
            <best_of> - number of simulations to run (over all argument sets), printing stats for the quickest. """
        test_data = list(args_iter)
        for runner_cls in self._runner_types:
            runner = runner_cls(func, *args)
            for _ in range(best_of):
                runner.run(test_data)
            print("")
            print(runner.format_best(**kwargs))
