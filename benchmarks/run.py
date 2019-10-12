#!/usr/bin/env python3

""" cProfile benchmarks for each lexer component. Counts are tailored for a reasonable running time. """

import sys

from .bench import bench


class ComponentBench:

    def __init__(self, steno_engine, search_engine, translations):
        self.steno_engine = steno_engine
        self.search_engine = search_engine
        self.translations = translations

    def _spaced_translations(self, n):
        items = [*self.translations.items()]
        step = len(items) // n
        return items[:step*n:step]

    def _spaced_results(self, n):
        translations = self._spaced_translations(n)
        query = self.steno_engine.lexer_query
        return [(k, w, query(k, w)) for k, w in translations]

    def run_lexer(self):
        bench(self.steno_engine.lexer_query, self._spaced_translations(5000))

    def make_board(self):
        bench(self._make_board, self._spaced_results(5000))

    def _make_board(self, keys, letters, result):
        self.steno_engine._board_engine.from_rules(result.rule_names(), result.unmatched_skeys())

    def make_graph(self):
        bench(self._make_graph, self._spaced_results(5000))

    def _make_graph(self, keys, letters, result):
        root = self.steno_engine._graph_engine.make_tree(letters, list(result), result.unmatched_skeys())
        graph = self.steno_engine._graph_engine.make_graph(root)
        node = graph.find_node_from_ref('#1')
        graph.render(node)

    def run_search(self):
        import random
        random.seed(123)
        prefixes = [w[:random.randint(1, len(w))] for k, w in self._spaced_translations(50000)]
        bench(self._run_search, zip(prefixes))

    def _run_search(self, letters):
        self.search_engine.search_translations(letters, count=100)

    def init_plover(self):
        from spectra_lexer import plover
        steno_dc = plover.dict_to_dc(self.translations, split_count=1)
        bench(plover.dc_to_dict, [(steno_dc,)] * 10)


def app_start():
    from spectra_lexer.app import StenoMain
    return StenoMain().build_app()


def app_analyze():
    from spectra_lexer.app import analyze
    analyze("--index=NUL", "--out=NUL", "--processes=1")


def app_index():
    from spectra_lexer.app import index
    index("--index=NUL", "--processes=1")


def main(_script:str="", operation:str="run_lexer", *argv:str) -> int:
    """ Application startup benchmarks also include import time.
        Only one run at a time is allowed, since imports are cached after that. """
    if operation.startswith("app"):
        func = globals()[operation]
        bench(func, max_lines=100)
    else:
        # Other benchmarks require an already-started app's engine components.
        app = app_start()
        steno_engine = app._steno_engine
        search_engine = app._search_engine
        translations = search_engine.get_translations()
        b = ComponentBench(steno_engine, search_engine, translations)
        getattr(b, operation)()
    return 0


if __name__ == '__main__':
    sys.exit(main(*sys.argv))
