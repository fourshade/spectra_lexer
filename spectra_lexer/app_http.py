""" Main module for the HTTP web application. """

import os
import sys
from typing import Callable

from spectra_lexer import SpectraOptions
from spectra_lexer.spc_lexer import TranslationFilter
from spectra_lexer.gui_engine import DisplayData, DisplayPage, GUIEngine, SearchResults
from spectra_lexer.gui_rest import RESTGUIApplication, RESTUpdate
from spectra_lexer.http.connect import HTTPConnectionHandler
from spectra_lexer.http.json import CustomJSONEncoder, JSONBinaryWrapper, RestrictedJSONDecoder
from spectra_lexer.http.service import HTTPDataService, HTTPFileService, HTTPGzipFilter, \
    HTTPContentTypeRouter, HTTPMethodRouter, HTTPPathRouter
from spectra_lexer.http.tcp import ThreadedTCPServer

HTTP_PUBLIC_DEFAULT = os.path.join(os.path.split(__file__)[0], "http_public")
JSON_DATA_CLASSES = [DisplayData, DisplayPage, RESTUpdate, SearchResults]


class HTTPApplication:
    """ Main HTTP application. """

    def __init__(self, app:RESTGUIApplication, log:Callable[[str], None]) -> None:
        self._app = app  # Main REST application.
        self._log = log  # Thread-safe logger.

    def build_server(self, root_dir:str) -> ThreadedTCPServer:
        """ Build an HTTP server object customized to Spectra's requirements. """
        decoder = RestrictedJSONDecoder(size_limit=100000, obj_limit=20, arr_limit=20)
        encoder = CustomJSONEncoder()
        for cls in JSON_DATA_CLASSES:
            encoder.add_data_class(cls)
        json_wrapper = JSONBinaryWrapper(self._app.run, decoder=decoder, encoder=encoder)
        data_service = HTTPDataService(json_wrapper, "application/json")
        compressed_service = HTTPGzipFilter(data_service, size_threshold=1000)
        file_service = HTTPFileService(root_dir)
        type_router = HTTPContentTypeRouter()
        type_router.add_route("application/json", compressed_service)
        post_router = HTTPPathRouter()
        post_router.add_route("/request", type_router)
        method_router = HTTPMethodRouter()
        method_router.add_route("GET", file_service)
        method_router.add_route("HEAD", file_service)
        method_router.add_route("POST", post_router)
        dispatcher = HTTPConnectionHandler(method_router, self._log)
        return ThreadedTCPServer(dispatcher)

    def run_server(self, server:ThreadedTCPServer, addr:str, port:int) -> int:
        """ Start the server and poll for connections indefinitely. """
        self._log("Server started.")
        try:
            server.start(addr, port)
        finally:
            server.shutdown()
        self._log("Server stopped.")
        return 0


def build_app(opts:SpectraOptions) -> HTTPApplication:
    """ Start with standard command-line options and build the app. """
    spectra = opts.compile()
    translations_paths = opts.translations_paths()
    index_path = opts.index_path()
    log = spectra.log
    io = spectra.resource_io
    search_engine = spectra.search_engine
    analyzer = spectra.analyzer
    graph_engine = spectra.graph_engine
    board_engine = spectra.board_engine
    log("Loading...")
    translations = io.load_json_translations(*translations_paths)
    search_engine.set_translations(translations)
    try:
        examples = io.load_json_examples(index_path)
    except OSError:
        # If there's no index, we really need one, so make one (and make it big).
        log("Building new index...")
        pairs = translations.items()
        examples = analyzer.compile_index(pairs, TranslationFilter.SIZE_LARGE)
        io.save_json_examples(index_path, examples)
    search_engine.set_examples(examples)
    gui_engine = GUIEngine(search_engine, analyzer, graph_engine, board_engine)
    gui_app = RESTGUIApplication(gui_engine)
    return HTTPApplication(gui_app, log)


def main() -> int:
    opts = SpectraOptions("Run Spectra as an HTTP web server.")
    opts.add("http-addr", "", "IP address or hostname for server.")
    opts.add("http-port", 80, "TCP port to listen for connections.")
    opts.add("http-dir", HTTP_PUBLIC_DEFAULT, "Root directory for public HTTP file service.")
    app = build_app(opts)
    server = app.build_server(opts.http_dir)
    return app.run_server(server, opts.http_addr, opts.http_port)


if __name__ == '__main__':
    sys.exit(main())
