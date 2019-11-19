#!/usr/bin/env python3

""" cProfile benchmarks for each lexer component. Counts are tailored for a reasonable running time. """

import sys

from .bench import bench


class ComponentBench:

    def __init__(self, engine) -> None:
        self._engine = engine

    def _translations(self) -> dict:
        return self._engine._translations.to_dict()

    def init_plover(self) -> None:
        from test import test_plover
        steno_dc = test_plover.dict_to_dc(self._translations(), split_count=1)
        bench(test_plover.dc_to_dict, [(steno_dc,)] * 10)

    def _spaced_translations(self, n:int) -> list:
        items = [*self._translations().items()]
        step = len(items) // n
        return items[:step*n:step]

    def run_search(self) -> None:
        import random
        random.seed(123)
        prefixes = [w[:random.randint(1, len(w))] for k, w in self._spaced_translations(50000)]
        bench(self._run_search, zip(prefixes))

    def _run_search(self, letters:str) -> None:
        self._engine._translations.search(letters, count=100)

    def run_lexer(self) -> None:
        bench(self._engine.lexer_query, self._spaced_translations(5000))

    def _spaced_results(self, n:int) -> list:
        translations = self._spaced_translations(n)
        query = self._engine.lexer_query
        return [(w, query(k, w)) for k, w in translations]

    def make_board(self) -> None:
        bench(self._make_board, self._spaced_results(5000))

    def _make_board(self, letters:str, result) -> None:
        self._engine._board_engine.generate(result.rule_ids(), result.unmatched_skeys())

    def make_graph(self) -> None:
        bench(self._make_graph, self._spaced_results(500))

    def _make_graph(self, letters:str, result) -> None:
        graph_engine = self._engine._graph_engine
        root = graph_engine.generate(letters, result.rule_ids(), result.rule_positions(), result.unmatched_skeys())
        for node in root:
            root.render(node)

    def run_analysis(self) -> None:
        bench(self._run_analysis, self._spaced_translations(500))

    def _run_analysis(self, keys:str, letters:str) -> None:
        self._engine.process_action("Query", [keys, letters])


def app_start():
    from spectra_lexer.base import StenoAppFactory
    return StenoAppFactory().build_app()


def app_index() -> None:
    from spectra_lexer.gui_none import index
    sys.argv += ["--index=NUL", "--processes=1"]
    index()


def main(script="", operation="run_lexer", *argv:str) -> int:
    """ Application startup benchmarks also include import time.
        Only one run at a time is allowed, since imports are cached after that. """
    sys.argv = [script, *argv]
    if operation.startswith("app"):
        func = globals()[operation]
        bench(func, max_lines=100)
    else:
        # Other benchmarks require an already-started app's engine components.
        app = app_start()
        b = ComponentBench(app._engine)
        getattr(b, operation)()
    return 0


if __name__ == '__main__':
    sys.exit(main(*sys.argv))
