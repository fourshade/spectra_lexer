#!/usr/bin/env python3

""" Primary entry point for Spectra's component benchmarks. """

import subprocess
import sys

from benchmarks.profilers import DetailedProfiler, RawProfiler
from benchmarks import tests

PROFILERS = {cls.__name__: cls() for cls in [RawProfiler, DetailedProfiler]}
SECTION_DELIM = '-' * 78


def main(script:str, operation="app_start", *argv:str) -> int:
    """ Some benchmarks also include import time.
        Imports are cached after the first run, so use subprocesses for each profiler. """
    if argv:
        pf_name, *args = argv
        if pf_name in PROFILERS:
            setup = getattr(tests, operation)
            func = setup(*map(int, args))
            profiler = PROFILERS[pf_name]
            profiler.run(func)
            results = profiler.format_best()
            print(f'Benchmark for {operation} using {pf_name}:\n\n{results}', end='')
            return 0
    print()
    for name in PROFILERS:
        cmd = (sys.executable, script, operation, name, *argv)
        result = subprocess.run(cmd, capture_output=True, text=True)
        print(f'{SECTION_DELIM}\n')
        if result.returncode:
            print(result.stderr)
        else:
            print(result.stdout)
    print(SECTION_DELIM)
    return 0


if __name__ == '__main__':
    sys.exit(main(*sys.argv))
