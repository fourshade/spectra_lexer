""" Main module for the HTTP web application. """

import os
import sys
from threading import Lock
from typing import Callable

from spectra_lexer import Spectra
from spectra_lexer.analysis import TranslationFilter
from spectra_lexer.engine import StenoEngine
from spectra_lexer.gui import DisplayData, DisplayPage, GUILayer, GUIOptions, GUIOutput, SearchResults
from spectra_lexer.http.connect import HTTPConnectionHandler
from spectra_lexer.http.json import CustomJSONEncoder, JSONBinaryWrapper, RestrictedJSONDecoder
from spectra_lexer.http.service import HTTPDataService, HTTPFileService, HTTPGzipFilter, \
    HTTPContentTypeRouter, HTTPMethodRouter, HTTPPathRouter
from spectra_lexer.http.tcp import ThreadedTCPServer
from spectra_lexer.util.cmdline import CmdlineOptions


HTTP_PUBLIC_DEFAULT = os.path.join(os.path.split(__file__)[0], "http_public")
JSON_DATA_CLASSES = [DisplayData, DisplayPage, SearchResults, GUIOutput]


class HTTPGUIApplication:
    """ Main HTTP application. """

    def __init__(self, gui:GUILayer) -> None:
        self._gui = gui      # Main steno GUI.
        self._lock = Lock()  # Lock to protect the main engine, which may not be thread-safe.

    def gui_call(self, *, action:str, args:list, options:dict) -> GUIOutput:
        """ Process a GUI app call. Input data includes a GUI action, its arguments (if any), and all options. """
        with self._lock:
            method = getattr(self._gui, action)
            opts = GUIOptions(options)
            self._gui.set_options(opts)
            return method(*args)


def build_server(engine:StenoEngine, root_dir:str, log:Callable[[str], None]) -> ThreadedTCPServer:
    """ Build an HTTP server object customized to Spectra's requirements. """
    gui = GUILayer(engine)
    app = HTTPGUIApplication(gui)
    decoder = RestrictedJSONDecoder(size_limit=100000, obj_limit=20, arr_limit=20)
    encoder = CustomJSONEncoder()
    for cls in JSON_DATA_CLASSES:
        encoder.add_data_class(cls)
    json_wrapper = JSONBinaryWrapper(app.gui_call, decoder=decoder, encoder=encoder)
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
    dispatcher = HTTPConnectionHandler(method_router, log)
    return ThreadedTCPServer(dispatcher)


def main() -> int:
    """ Start with standard HTTP configuration settings as command-line options and build the engine.
        Then start the server and poll for connections indefinitely. """
    opts = CmdlineOptions("Run Spectra as an HTTP web server.")
    opts.add("http-addr", "", "IP address or hostname for server.")
    opts.add("http-port", 80, "TCP port to listen for connections.")
    opts.add("http-dir", HTTP_PUBLIC_DEFAULT, "Root directory for public HTTP file service.")
    spectra = Spectra(opts)
    spectra.log("Loading...")
    engine = spectra.build_engine()
    translations_files = spectra.translations_paths()
    engine.load_translations(*translations_files)
    index_file = spectra.index_path()
    try:
        engine.load_examples(index_file)
    except OSError:
        # If there's no index, we really need one, so make one (and make it big).
        spectra.log("Building new index...")
        engine.compile_examples(TranslationFilter.SIZE_LARGE, index_file)
    server = build_server(engine, opts.http_dir, spectra.log)
    spectra.log("Server started.")
    try:
        server.start(opts.http_addr, opts.http_port)
    finally:
        server.shutdown()
    spectra.log("Server stopped.")
    return 0


if __name__ == '__main__':
    sys.exit(main())
