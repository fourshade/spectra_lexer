""" Main module for the HTTP web application. """

import os
import sys

from spectra_lexer import SpectraOptions
from spectra_lexer.gui_engine import GUIEngine, SearchResults
from spectra_lexer.gui_ext import GUIExtension
from spectra_lexer.gui_rest import RESTDisplay, RESTDisplayPage, RESTGUIApplication, RESTUpdate
from spectra_lexer.http.connect import HTTPConnectionHandler
from spectra_lexer.http.json import CustomJSONEncoder, JSONBinaryWrapper, RestrictedJSONDecoder
from spectra_lexer.http.service import HTTPDataService, HTTPFileService, HTTPGzipFilter, \
    HTTPContentTypeRouter, HTTPMethodRouter, HTTPPathRouter
from spectra_lexer.http.tcp import ThreadedTCPServer

HTTP_PUBLIC_DEFAULT = os.path.join(os.path.split(__file__)[0], "http_public")
JSON_DATA_CLASSES = [RESTDisplay, RESTDisplayPage, RESTUpdate, SearchResults]


def build_app(opts:SpectraOptions) -> tuple:
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
    gui_engine = GUIEngine(search_engine, analyzer, graph_engine, board_engine)
    gui_ext = GUIExtension(io, search_engine, analyzer, index_path, "")
    gui_ext.load_translations(*translations_paths)
    gui_ext.load_initial()
    return RESTGUIApplication(gui_engine), log


def build_dispatcher(app:RESTGUIApplication, root_dir:str, *args) -> HTTPConnectionHandler:
    """ Build an HTTP server object customized to Spectra's requirements. """
    decoder = RestrictedJSONDecoder(size_limit=100000, obj_limit=20, arr_limit=20)
    encoder = CustomJSONEncoder()
    for cls in JSON_DATA_CLASSES:
        encoder.add_data_class(cls)
    json_wrapper = JSONBinaryWrapper(app.run, decoder=decoder, encoder=encoder)
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
    return HTTPConnectionHandler(method_router, *args)


def main() -> int:
    """ Build the server, start it, and poll for connections indefinitely. """
    opts = SpectraOptions("Run Spectra as an HTTP web server.")
    opts.add("http-addr", "", "IP address or hostname for server.")
    opts.add("http-port", 80, "TCP port to listen for connections.")
    opts.add("http-dir", HTTP_PUBLIC_DEFAULT, "Root directory for public HTTP file service.")
    app, log = build_app(opts)
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
