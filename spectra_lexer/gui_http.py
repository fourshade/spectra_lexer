""" Main module for the HTTP web application. """

import os
import sys
from threading import Lock

from spectra_lexer.app import StenoApplication, StenoGUIOutput
from spectra_lexer.base import Spectra
from spectra_lexer.display import DisplayData, DisplayPage
from spectra_lexer.http.connect import HTTPConnectionHandler
from spectra_lexer.http.service import HTTPFileService, HTTPGzipFilter, HTTPJSONService, \
    HTTPMethodRouter, HTTPPathRouter
from spectra_lexer.http.tcp import ThreadedTCPServer
from spectra_lexer.search import SearchResults
from spectra_lexer.util.cmdline import CmdlineOption
from spectra_lexer.util.json import CustomJSONEncoder, RestrictedJSONDecoder

JSON_DATA_CLASSES = [DisplayData, DisplayPage, SearchResults, StenoGUIOutput]
HTTP_PUBLIC_DEFAULT = os.path.join(os.path.split(__file__)[0], "http_public")


class StenoAppService(HTTPJSONService):
    """ Main HTTP service for handling requests to the steno app. """

    def __init__(self, app:StenoApplication, *args) -> None:
        super().__init__(*args)
        self._app = app      # Main steno app.
        self._lock = Lock()  # Lock to protect the main app, which may not be thread-safe.

    def process(self, params:dict, *args) -> StenoGUIOutput:
        """ The decoded object is a params dict with the action, its arguments (if any), and all options. """
        with self._lock:
            action = params["action"]
            args = params["args"]
            options = params["options"]
            method = getattr(self._app, "gui_" + action)
            return method(*args, **options)


class SpectraHttp(Spectra):
    """ Run the Spectra HTTP web application. """

    # Standard HTTP configuration settings are command-line options.
    address: str = CmdlineOption("--http-addr", "", "IP address or hostname for server.")
    port: int = CmdlineOption("--http-port", 80, "TCP port to listen for connections.")
    directory: str = CmdlineOption("--http-dir", HTTP_PUBLIC_DEFAULT, "Root directory for public HTTP file service.")

    def build_app_service(self) -> StenoAppService:
        app = self.build_app()
        self.load_app(app)
        decoder = RestrictedJSONDecoder(size_limit=100000, obj_limit=20, arr_limit=20)
        encoder = CustomJSONEncoder()
        for cls in JSON_DATA_CLASSES:
            encoder.add_data_class(cls)
        app_service = StenoAppService(app, decoder, encoder)
        compressed_service = HTTPGzipFilter(app_service, size_threshold=1000)
        return compressed_service

    def build_server(self, *args) -> ThreadedTCPServer:
        file_service = HTTPFileService(self.directory)
        app_service = self.build_app_service()
        post_router = HTTPPathRouter()
        post_router.add_route("/request", app_service)
        method_router = HTTPMethodRouter()
        method_router.add_route("GET", file_service)
        method_router.add_route("HEAD", file_service)
        method_router.add_route("POST", post_router)
        dispatcher = HTTPConnectionHandler(method_router, *args)
        server = ThreadedTCPServer(dispatcher)
        return server

    def run(self) -> int:
        """ Build the app, start the server, and poll for connections indefinitely. """
        log = self.build_logger().log
        log("Loading...")
        server = self.build_server(log)
        log("Server started.")
        try:
            server.start(self.address, self.port)
        finally:
            server.shutdown()
        log("Server stopped.")
        return 0




http_main = SpectraHttp.main

if __name__ == '__main__':
    sys.exit(http_main())
