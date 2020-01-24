#!/usr/bin/env python3

""" cProfile benchmarks for each lexer component. Counts are tailored for a reasonable running time. """

import subprocess
import sys

from .bench import MultiProfiler, ProfileTestRunner, RawTestRunner

PROFILER_TYPES = [RawTestRunner, ProfileTestRunner]


class ComponentBench:

    def __init__(self, engine, profiler) -> None:
        self._engine = engine
        self._profiler = profiler

    def _translations(self) -> dict:
        return self._engine._translations

    def init_plover(self) -> None:
        from test import test_plover
        steno_dc = test_plover.dict_to_dc(self._translations(), split_count=1)
        self._profiler.run(test_plover.dc_to_dict, [(steno_dc,)] * 10)

    def _spaced_translations(self, n:int) -> list:
        items = [*self._translations().items()]
        step = len(items) // n
        return items[:step*n:step]

    def run_search(self) -> None:
        import random
        random.seed(123)
        prefixes = [w[:random.randint(1, len(w))] for k, w in self._spaced_translations(50000)]
        self._profiler.run(self._engine.search, zip(prefixes))

    def run_lexer(self) -> None:
        self._profiler.run(self._engine.analyze, self._spaced_translations(5000))

    def _spaced_results(self, n:int) -> list:
        translations = self._spaced_translations(n)
        query = self._engine.analyze
        return [(query(k, w),) for k, w in translations]

    def make_display(self) -> None:
        self._profiler.run(self._engine.display, self._spaced_results(500))


def app_start():
    from spectra_lexer.base import Spectra
    prg = Spectra()
    app = prg.build_app()
    prg.load_app(app)
    return app


def app_index() -> None:
    from spectra_lexer.gui_none import index_main
    sys.argv += ["--index=NUL", "--processes=1"]
    index_main()


def main(script="", operation="run_lexer", *argv:str) -> int:
    sys.argv = [script, *argv]
    if operation.startswith("sub"):
        _, idx, operation = operation.split("|")
        p_type = PROFILER_TYPES[int(idx)]
        func = globals()[operation]
        profiler = MultiProfiler(p_type)
        profiler.run(func, max_lines=100)
    elif operation.startswith("app"):
        # Application startup benchmarks also include import time.
        # Since imports are cached after the first run, subprocesses must be used.
        for i in range(len(PROFILER_TYPES)):
            cmd = (sys.executable, '-m', 'benchmarks.run', f'sub|{i}|{operation}')
            subprocess.run(cmd, check=True)
    else:
        # Other benchmarks require an already-started app's engine.
        app = app_start()
        profiler = MultiProfiler(*PROFILER_TYPES)
        b = ComponentBench(app._engine, profiler)
        getattr(b, operation)()
    return 0


if __name__ == '__main__':
    sys.exit(main(*sys.argv))
