""" Main module for the HTTP web application. """

import os
import sys

from spectra_lexer import Spectra, SpectraOptions
from spectra_lexer.gui_engine import GUIEngine
from spectra_lexer.gui_rest import RESTGUIApplication
from spectra_lexer.http.connect import HTTPConnectionHandler
from spectra_lexer.http.json import JSONCodec, JSONObjectProcessor, RestrictedJSONDecoder
from spectra_lexer.http.service import HTTPDataService, HTTPFileService, HTTPGzipFilter, \
    HTTPContentTypeRouter, HTTPMethodRouter, HTTPPathRouter
from spectra_lexer.http.tcp import ThreadedTCPServer

HTTP_PUBLIC_DEFAULT = os.path.join(os.path.split(__file__)[0], "http_public")


def build_app(spectra:Spectra) -> RESTGUIApplication:
    """ Start with standard command-line options and build the app. """
    io = spectra.resource_io
    search_engine = spectra.search_engine
    analyzer = spectra.analyzer
    graph_engine = spectra.graph_engine
    board_engine = spectra.board_engine
    translations_paths = spectra.translations_paths
    index_path = spectra.index_path
    gui_engine = GUIEngine(io, search_engine, analyzer, graph_engine, board_engine, translations_paths, index_path)
    gui_engine.load_initial()
    return RESTGUIApplication(gui_engine)


def build_dispatcher(app:RESTGUIApplication, root_dir:str, *args) -> HTTPConnectionHandler:
    """ Build an HTTP server object customized to Spectra's requirements. """
    decoder = RestrictedJSONDecoder(size_limit=100000, obj_limit=20, arr_limit=20)
    codec = JSONCodec(decoder)
    processor = JSONObjectProcessor(app, codec)
    data_service = HTTPDataService(processor)
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
    return HTTPConnectionHandler(method_router, *args)


def main() -> int:
    """ Build the server, start it, and poll for connections indefinitely. """
    opts = SpectraOptions("Run Spectra as an HTTP web server.")
    opts.add("http-addr", "", "IP address or hostname for server.")
    opts.add("http-port", 80, "TCP port to listen for connections.")
    opts.add("http-dir", HTTP_PUBLIC_DEFAULT, "Root directory for public HTTP file service.")
    spectra = Spectra(opts)
    log = spectra.logger.log
    log("Loading HTTP server...")
    app = build_app(spectra)
    dispatcher = build_dispatcher(app, opts.http_dir, log)
    server = ThreadedTCPServer(dispatcher)
    log("Server started.")
    try:
        server.start(opts.http_addr, opts.http_port)
    finally:
        server.shutdown()
    log("Server stopped.")
    return 0


if __name__ == '__main__':
    sys.exit(main())
