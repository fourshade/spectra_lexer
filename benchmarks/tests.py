""" Benchmark test generators for each application component. Counts are tailored for a reasonable running time. """


# Setup functions for fixtures and test data. Some benchmarks count import time, so all imports are local.

def _spectra():
    from spectra_lexer import Spectra
    return Spectra()


def _http_app():
    from spectra_lexer.app_http import build_app
    return build_app(_spectra())


def _get_translations() -> dict:
    spectra = _spectra()
    paths = spectra.translations_paths
    return spectra.resource_io.load_json_translations(*paths)


def _search_fn(patterns:list, **kwargs):
    translations = _get_translations()
    search_engine = _spectra().search_engine
    search_engine.set_translations(translations)
    def run() -> None:
        for p in patterns:
            search_engine.search(p, **kwargs)
    return run


def _random(seed:int=None):
    from random import Random
    return Random(seed)


def _random_translations(n:int) -> list:
    items = _get_translations().items()
    return _random(n).sample(list(items), n)


def _random_prefixes(n:int) -> list:
    samples = _random_translations(n)
    rnd = _random(n)
    return [w[:rnd.randint(1, len(w))] for _, w in samples]


def _random_regexes(n:int) -> list:
    prefixes = _random_prefixes(n//2)
    alpha = 'abcdefghijklmnopqrstuvwxyz'
    rnd = _random(n)
    return prefixes + [s.replace(rnd.choice(alpha), '.')+'+' for s in prefixes]


def _random_analyses(n:int) -> list:
    samples = _random_translations(n)
    analyzer = _spectra().analyzer
    return [analyzer.query(k, w) for k, w in samples]


# Main benchmark functions. Each returns a no-arg callable suitable for profiling a particular component.

def app_start():
    return _http_app


def search(n=50000):
    prefixes = _random_prefixes(n)
    return _search_fn(prefixes, count=100)


def search_regex(n=1000):
    patterns = _random_regexes(n)
    return _search_fn(patterns, count=100, mode_regex=True)


def lexer(n=10000):
    samples = _random_translations(n)
    analyzer = _spectra().analyzer
    def run() -> None:
        for k, w in samples:
            analyzer.query(k, w)
    return run


def index(n=10000):
    samples = _random_translations(n)
    analyzer = _spectra().analyzer
    def run() -> None:
        analyzer.compile_index(samples, process_count=1)
    return run


def graph(n=10000):
    rules = _random_analyses(n)
    graph_engine = _spectra().graph_engine
    def run() -> None:
        for rule in rules:
            graph_engine.graph(rule).draw()
    return run


def board(n=10000):
    rules = _random_analyses(n)
    board_engine = _spectra().board_engine
    def run() -> None:
        for rule in rules:
            board_engine.draw_rule(rule)
    return run


def gui_query(n=1000):
    samples = _random_translations(n)
    app = _http_app()
    def run() -> None:
        for keys, letters in samples:
            app.do_query(keys, letters)
    return run


def http_query(n=1000):
    from spectra_lexer.app_http import build_dispatcher
    import io, json
    queries = []
    samples = _random_translations(n)
    for item in samples:
        obj = {"action": "query",
               "args": item,
               "options": {}}
        content = json.dumps(obj).encode('utf8')
        length = str(len(content)).encode('utf8')
        request = [b"POST /request HTTP/1.1",
                   b"Accept-Encoding: gzip",
                   b"Content-Type: application/json",
                   b"Content-Length: " + length,
                   b"",
                   content]
        queries.append(b"\r\n".join(request))
    app = _http_app()
    dispatcher = build_dispatcher(app)
    def run() -> None:
        for data in queries:
            stream = io.BytesIO(data)
            dispatcher.handle_connection(stream, lambda s: None)
    return run


def plover_convert(n=10):
    from test import test_plover
    translations = _get_translations()
    steno_dc = test_plover.dict_to_dc(translations, split_count=1)
    def run() -> None:
        for _ in range(n):
            test_plover.dc_to_dict(steno_dc)
    return run
