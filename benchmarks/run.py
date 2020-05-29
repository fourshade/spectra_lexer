#!/usr/bin/env python3

""" cProfile benchmarks for each lexer component. Counts are tailored for a reasonable running time. """

from random import Random
import subprocess
import sys

from .bench import MultiProfiler, ProfileTestRunner, RawTestRunner

PROFILER_TYPES = [RawTestRunner, ProfileTestRunner]

_translations = {}
def load_translations() -> dict:
    if not _translations:
        from spectra_lexer import SpectraOptions
        from spectra_lexer import TranslationsIO
        opts = SpectraOptions()
        paths = opts.translations_paths()
        io = TranslationsIO()
        _translations.update(io.load_json_translations(*paths))
    return _translations


def _random_translations(n) -> list:
    items = load_translations().items()
    return Random(n).sample(list(items), n)


def app_start():
    from spectra_lexer import SpectraOptions
    from spectra_lexer.app_http import build_app
    opts = SpectraOptions()
    return build_app(opts)


def app_index() -> None:
    from spectra_lexer.app_index import main as index_main
    sys.argv += ["--index=NUL", "--processes=1"]
    index_main()


class ComponentBench:

    def __init__(self, profiler) -> None:
        self._profiler = profiler

    def init_plover(self) -> None:
        from test import test_plover
        translations = load_translations()
        steno_dc = test_plover.dict_to_dc(translations, split_count=1)
        self._profiler.run(test_plover.dc_to_dict, [(steno_dc,)] * 10)

    def run_search(self, n=50000) -> None:
        from random import Random
        from spectra_lexer import SpectraOptions
        opts = SpectraOptions()
        spectra = opts.compile()
        translations = load_translations()
        spectra.search_engine.set_translations(translations)
        samples = _random_translations(n)
        rnd = Random(n)
        prefixes = [w[:rnd.randint(1, len(w))] for k, w in samples]
        counts = [100] * n
        self._profiler.run(spectra.search_engine.search, zip(prefixes, counts))

    def run_lexer(self, n=5000) -> None:
        from spectra_lexer import SpectraOptions
        opts = SpectraOptions()
        spectra = opts.compile()
        samples = _random_translations(n)
        self._profiler.run(spectra.analyzer.query, samples)

    def run_gui(self, n=500) -> None:
        samples = _random_translations(n)
        app = app_start()
        self._profiler.run(app._gui.query, zip(samples))

    def run_http(self, n=500) -> None:
        from spectra_lexer.http.tcp import TCPConnection, TCPServer
        import io, json
        args_list = []
        samples = _random_translations(n)
        for item in samples:
            obj = {"action": "query",
                   "args": [item],
                   "options": {}}
            content = json.dumps(obj).encode('utf8')
            length = str(len(content)).encode('utf8')
            request = [b"POST /request HTTP/1.1",
                       b"Accept-Encoding: gzip",
                       b"Content-Type: application/json",
                       b"Content-Length: " + length,
                       b"",
                       content]
            args_list.append((b"\r\n".join(request),))
        app = app_start()
        app._log = lambda s: None
        server = app.build_server(".")
        def dispatch(data):
            stream = io.BytesIO(data)
            conn = TCPConnection(stream, "127.0.0.1", 80)
            # Avoid threading issues by connecting with the base class.
            TCPServer.connect(server, conn)
        self._profiler.run(dispatch, args_list)


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
        profiler = MultiProfiler(*PROFILER_TYPES)
        b = ComponentBench(profiler)
        getattr(b, operation)()
    return 0


if __name__ == '__main__':
    sys.exit(main(*sys.argv))
