#!/usr/bin/env python3

""" cProfile benchmarks for each lexer component. """

import cProfile
import pstats
from io import StringIO
import itertools

from spectra_lexer.format.cascaded_text import CascadedTextDisplay
from spectra_lexer.lexer import StenoLexer
from spectra_lexer.rules.lexer_dict import LexerDictionary
from test.test_all import TEST_DATA


def test_bench_load():
    bench(LexerDictionary, (), count=50, best_of=3, max_lines=50, strip_to_level=1)


def test_bench_parse():
    lexer = StenoLexer()
    bench(_parse_all, (lexer,), count=500, best_of=3, max_lines=50, strip_to_level=1)


def test_bench_display():
    lexer = StenoLexer()
    results = _parse_all(lexer)
    bench(_display_all, (results,), count=500, best_of=3, max_lines=50, strip_to_level=1)


def _parse_all(lexer):
    return [lexer.parse(d[0], d[1]) for d in TEST_DATA]


def _display_all(results):
    return [CascadedTextDisplay(r.make_tree()) for r in results]


def bench(func, args, count=1, best_of=1, max_lines=50, strip_to_level=None):
    """
    Measure and print the execution time for each method composing a given function with given test arguments.

    func:           function to profile.
    args:           tuple containing test arguments for the function
    count:          times to call the function during one simulation
    best_of:        number of simulations to run (over all argument sets), returning stats for the quickest.
    max_lines:      maximum number of methods to print profiles on.
    strip_to_level: how many directory levels do we leave in each file listing?
                        None: C:/ProgramData/Anaconda3/lib/test.py
                        0: test.py
                        1: lib/test.py
    """
    best_pr = None
    best_time = None
    for _ in range(best_of):
        pr = cProfile.Profile()
        pr.enable()
        for _ in range(count):
            func(*args)
        pr.disable()
        pr.create_stats()
        max_ct = max(s[3] for s in pr.stats.values())
        if best_time is None or max_ct < best_time:
            best_time = max_ct
            best_pr = pr
    if best_pr is not None:
        s_buf = StringIO()
        ps = pstats.Stats(best_pr, stream=s_buf).sort_stats('cumulative')
        ps.print_stats(max_lines)
        print("\nBenchmark for {}, best of {}:\n".format(func.__qualname__, best_of))
        for line in itertools.dropwhile(lambda s: "ncalls" not in s, s_buf.getvalue().split("\n")):
            fields = line.split(maxsplit=5)
            if len(fields) > 5:
                if strip_to_level is not None:
                    fields[5] = "\\".join(fields[5].split('\\')[-strip_to_level-1:])
                print("".join((*[fields[i].rjust(10) for i in (0, 1, 3)], "  ", fields[5])))
            else:
                print(line)
