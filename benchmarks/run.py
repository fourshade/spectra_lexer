#!/usr/bin/env python3

""" cProfile benchmarks for each lexer component. Counts are tailored for a reasonable running time. """

import random
import sys

from .bench import bench


def _on_input(ifunc, engine, operation, n=5000):
    bench(operation, ifunc(engine, n), count=n)


def _spaced_translations(engine, n=None):
    items = [*engine._analyzer._translations]
    if n is None:
        return items
    step = len(items) // n
    return items[::step]


def _spaced_rules(engine, n):
    translations = _spaced_translations(engine, n)
    query = engine.lexer_query
    return zip([query(k, w) for k, w in translations])


def run_lexer(engine):
    _on_input(_spaced_translations, engine, engine.lexer_query)


def make_board(engine):
    _on_input(_spaced_rules, engine, engine.board_from_rule)


def make_graph(engine):
    _on_input(_spaced_rules, engine, lambda r: engine.graph_generate(r).render(ref='1'))


def run_search(engine):
    from spectra_lexer.steno.search.translations import TranslationsDictionary
    random.seed(123)
    translations = _spaced_translations(engine)
    prefixes_and_counts = [(letters[:random.randint(1, len(letters))], 100) for keys, letters in translations]
    d = TranslationsDictionary(translations)
    bench(d.search, prefixes_and_counts, count=50000)


def init_plover(engine):
    from spectra_lexer.plover.parser import PloverTranslationParser
    from spectra_lexer.plover.types import PloverEngine
    translations = dict(_spaced_translations(engine))
    plover = PloverEngine.test(translations, split_count=1)
    parser = PloverTranslationParser(plover)
    bench(parser.convert_dicts, count=10)


def app_start():
    from spectra_lexer.app import StenoApplication
    return StenoApplication()


def app_analyze():
    from spectra_lexer import analyze
    analyze("--index-file=NUL", "--rules-out=NUL")


def app_index():
    from spectra_lexer import index
    index("--index-file=NUL")


def main(_script:str="", operation:str="run_lexer", *argv:str) -> int:
    """ Application startup benchmarks also include import time.
        Only one run at a time is allowed, since imports are cached after that. """
    func = globals()[operation]
    if operation.startswith("app"):
        bench(func, count=1, best_of=1, max_lines=100)
    # Other benchmarks require an already-started app engine.
    func(app_start()._engine)
    return 0


if __name__ == '__main__':
    sys.exit(main(*sys.argv))
