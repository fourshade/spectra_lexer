#!/usr/bin/env python3

from cProfile import Profile
from io import StringIO
from itertools import cycle, islice
from pstats import Stats
from time import time


class BaseTestRunner:

    def __init__(self, func, setup) -> None:
        self.func = func
        self.setup = setup
        self.stats = []

    def run(self, test_data) -> None:
        """ Evaluate a function using test data. """
        self.setup()
        func = self.func
        timer = self.on()
        for t in test_data:
            func(*t)
        self.off(timer)

    def on(self):
        raise NotImplementedError

    def off(self, timer) -> None:
        raise NotImplementedError

    def format_best(self, **kwargs) -> str:
        raise NotImplementedError


class RawTestRunner(BaseTestRunner):

    def on(self) -> float:
        return time()

    def off(self, start_time:float) -> None:
        self.stats.append(time() - start_time)

    def format_best(self, **kwargs) -> str:
        return f"raw time = {min(self.stats):.3f}s\n"


class ProfileTestRunner(BaseTestRunner):

    def on(self) -> Profile:
        pr = Profile()
        pr.enable()
        return pr

    def off(self, pr:Profile) -> None:
        pr.disable()
        pr.create_stats()
        self.stats.append(pr)

    def format_best(self, *, max_lines=50, strip_to_level=1, **kwargs) -> str:
        """ Format a string with the execution time for each method during the quickest run.
        :param max_lines:        maximum number of methods to print profiles on.
        :param strip_to_level:   how many directory levels do we leave in each file listing?
                                 None: C:\\ProgramData\\Anaconda3\\lib\\test.py
                                 0: test.py
                                 1: lib\\test.py """
        colwidths = [12, 7, None, 7, None]
        colsep = "   "
        best_pr = min(self.stats, key=lambda p: max(s[3] for s in p.stats.values()))
        s_buf = StringIO()
        ps = Stats(best_pr, stream=s_buf).sort_stats('cumulative')
        ps.print_stats(max_lines)
        sections = ["Benchmark for ", self.func.__qualname__ , ", best of ", str(len(self.stats)), ":\n\n"]
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


def bench(func, args_iter=((),), setup=lambda: None, *, count=None, best_of=1, **kwargs) -> None:
    """ Measure and print the execution time for a given function with given test arguments.
    :param func:             function to profile.
    :param args_iter:        iterable of tuples containing positional test arguments, one tuple per test.
    :param count:            total number of tests in a single timed simulation. Cycles over args_iter if longer.
    :param best_of:          number of simulations to run (over all argument sets), returning stats for the quickest.
    :param setup:            optional function to call before each simulation. """
    if count is not None:
        args_iter = islice(cycle(args_iter), count)
    test_data = list(args_iter)
    for runner_cls in (RawTestRunner, ProfileTestRunner):
        runner = runner_cls(func, setup)
        for _ in range(best_of):
            runner.run(test_data)
        print("")
        print(runner.format_best(**kwargs))
