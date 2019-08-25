#!/usr/bin/env python3

import cProfile
from io import StringIO
from itertools import cycle, islice
import pstats


def bench(func, args_iter=((),), setup=None, *, count=1, best_of=3, valid_exc_types=(), max_lines=50, strip_to_level=1):
    """
    Measure and print the execution time for each method composing a given function with given test arguments.
    :param func:             function to profile.
    :param args_iter:        iterable of tuples containing positional test arguments, one tuple per test.
    :param count:            total number of tests in a single timed simulation. Cycles over contents of args_iter.
    :param best_of:          number of simulations to run (over all argument sets), returning stats for the quickest.
    :param setup:            optional function to call before each simulation.
    :param valid_exc_types:  sequence of exception types to suppress and count.
    :param max_lines:        maximum number of methods to print profiles on.
    :param strip_to_level:   how many directory levels do we leave in each file listing?
                             None: C:\\ProgramData\\Anaconda3\\lib\\test.py
                             0: test.py
                             1: lib\\test.py
    """
    profiles = []
    test_data = list(args_iter)
    for _ in range(best_of):
        if setup is not None:
            setup()
        sim_runs = islice(cycle(test_data), count)
        pr = cProfile.Profile()
        pr.enable()
        _run(func, sim_runs, valid_exc_types)
        pr.disable()
        pr.create_stats()
        profiles.append(pr)
    best_pr = min(profiles, key=lambda p: max(s[3] for s in p.stats.values()))
    stats = _format_stats(best_pr, max_lines)
    colwidths = [12, 7, None, 7, None]
    colsep = "   "
    fn_name = getattr(func, "__qualname__", "????")
    print(f"\nBenchmark for {fn_name}, best of {best_of}:\n")
    for line in stats.splitlines()[5:]:
        if line.strip():
            *fields, path = line.split(maxsplit=5)
            if strip_to_level is not None:
                path_segments = path.split('\\')
                stripped_segments = path_segments[-strip_to_level-1:]
                path = "\\".join(stripped_segments)
            fields = [f.rjust(w) for f, w in zip(fields, colwidths) if w is not None]
            print(*fields, path, sep=colsep)


def _format_stats(pr, max_lines):
    s_buf = StringIO()
    ps = pstats.Stats(pr, stream=s_buf).sort_stats('cumulative')
    ps.print_stats(max_lines)
    return s_buf.getvalue()


def _run(func, arg_tuples, valid_exc_types):
    """ Evaluates a test function, incrementing a counter on any valid exception and printing the total. """
    count = 0
    for t in arg_tuples:
        try:
            func(*t)
        except valid_exc_types:
            count += 1
    if count:
        print("Total exceptions:", count)
