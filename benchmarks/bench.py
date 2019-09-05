#!/usr/bin/env python3

import cProfile
from io import StringIO
from itertools import cycle, islice
import pstats
from time import time


def bench(func, args_iter=((),), setup=lambda: None, *, count=1, best_of=3, max_lines=50, strip_to_level=1):
    """
    Measure and print the execution time for each method composing a given function with given test arguments.
    :param func:             function to profile.
    :param args_iter:        iterable of tuples containing positional test arguments, one tuple per test.
    :param count:            total number of tests in a single timed simulation. Cycles over contents of args_iter.
    :param best_of:          number of simulations to run (over all argument sets), returning stats for the quickest.
    :param setup:            optional function to call before each simulation.
    :param max_lines:        maximum number of methods to print profiles on.
    :param strip_to_level:   how many directory levels do we leave in each file listing?
                             None: C:\\ProgramData\\Anaconda3\\lib\\test.py
                             0: test.py
                             1: lib\\test.py
    """
    test_data = list(args_iter)
    raw_runner = RawTestRunner(func, test_data, setup)
    raw_runner.run(count, best_of)
    pr_runner = ProfileTestRunner(func, test_data, setup)
    pr_runner.run(count, best_of)
    print(f"\nBenchmark for {func.__qualname__}, best of {best_of}:\n")
    raw_runner.print_best()
    pr_runner.print_best(max_lines, strip_to_level)


class BaseTestRunner:

    def __init__(self, func, test_data, setup):
        self.func = func
        self.test_data = test_data
        self.setup = setup
        self.stats = []

    def run(self, count, best_of=1):
        """ Evaluates a test function. """
        for _ in range(best_of):
            self.setup()
            func = self.func
            arg_tuples = islice(cycle(self.test_data), count)
            timer = self.on()
            for t in arg_tuples:
                func(*t)
            self.off(timer)

    def on(self):
        raise NotImplementedError

    def off(self, timer):
        raise NotImplementedError


class RawTestRunner(BaseTestRunner):

    def on(self):
        return time()

    def off(self, start_time):
        self.stats.append(time() - start_time)

    def print_best(self):
        print(f"raw time = {min(self.stats):.3f}s\n")


class ProfileTestRunner(BaseTestRunner):

    def on(self):
        pr = cProfile.Profile()
        pr.enable()
        return pr

    def off(self, pr):
        pr.disable()
        pr.create_stats()
        self.stats.append(pr)

    def print_best(self, max_lines, strip_to_level):
        colwidths = [12, 7, None, 7, None]
        colsep = "   "
        best_pr = min(self.stats, key=lambda p: max(s[3] for s in p.stats.values()))
        s_buf = StringIO()
        ps = pstats.Stats(best_pr, stream=s_buf).sort_stats('cumulative')
        ps.print_stats(max_lines)
        for line in s_buf.getvalue().splitlines()[5:]:
            if line.strip():
                *fields, path = line.split(maxsplit=5)
                if strip_to_level is not None:
                    path_segments = path.split('\\')
                    stripped_segments = path_segments[-strip_to_level-1:]
                    path = "\\".join(stripped_segments)
                fields = [f.rjust(w) for f, w in zip(fields, colwidths) if w is not None]
                print(*fields, path, sep=colsep)
