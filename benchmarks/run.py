#!/usr/bin/env python3

""" cProfile benchmarks for each lexer component. Counts are tailored for a reasonable running time. """

import sys

from .bench import bench


class ComponentBench:

    def __init__(self, engine):
        self.engine = engine
        self.translations = engine._translations
        self.n = 5000

    def _run(self, *args):
        bench(*args, count=self.n)

    def _spaced_translations(self):
        items = [*self.translations.items()]
        step = len(items) // self.n
        return items[::step]

    def _spaced_rules(self):
        translations = self._spaced_translations()
        query = self.engine.lexer_query
        return zip([query(k, w) for k, w in translations])

    def run_lexer(self):
        self._run(self.engine.lexer_query, self._spaced_translations())

    def make_board(self):
        self._run(self.engine.board_from_rule, self._spaced_rules())

    def make_graph(self):
        self._run(lambda r: self.engine.graph_generate(r).render(ref='#R_0'), self._spaced_rules())

    def run_search(self):
        import random
        self.n = 50000
        random.seed(123)
        translations = self.translations
        prefixes_and_counts = [(letters[:random.randint(1, len(letters))], 100) for letters in translations.values()]
        self._run(translations.search, prefixes_and_counts)

    def init_plover(self):
        from spectra_lexer.plover.parser import PloverTranslationParser
        from spectra_lexer.plover.types import FakePloverEngine
        self.n = 10
        plover = FakePloverEngine(self.translations, split_count=1)
        parser = PloverTranslationParser(plover)
        self._run(parser.convert_dicts)


def app_start():
    from spectra_lexer.app import StenoMain
    return StenoMain().build_app()


def app_analyze():
    from spectra_lexer.app import analyze
    analyze("--index=NUL", "--out=NUL")


def app_index():
    from spectra_lexer.app import index
    index("--index=NUL")


def main(_script:str="", operation:str="run_lexer", *argv:str) -> int:
    """ Application startup benchmarks also include import time.
        Only one run at a time is allowed, since imports are cached after that. """
    if operation.startswith("app"):
        func = globals()[operation]
        bench(func, count=1, best_of=1, max_lines=100)
    else:
        # Other benchmarks require an already-started app's engine.
        engine = app_start()._engine
        b = ComponentBench(engine)
        getattr(b, operation)()
    return 0


if __name__ == '__main__':
    sys.exit(main(*sys.argv))
