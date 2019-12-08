""" Main module for the HTTP web application. """

import os
import sys
from threading import Lock
from traceback import format_exc
from typing import Callable

from spectra_lexer.app import StenoApplication, StenoGUIOutput
from spectra_lexer.base import Spectra
from spectra_lexer.display import DisplayData, DisplayPage
from spectra_lexer.http import HTTPFileService, HTTPJSONService, HTTPMethodRouter, HTTPPathRouter, HTTPServer
from spectra_lexer.search import SearchResults
from spectra_lexer.util.cmdline import CmdlineOption

HTTP_PUBLIC_DEFAULT = os.path.join(os.path.split(__file__)[0], "http_public")


class StenoAppService(HTTPJSONService):
    """ Main HTTP service for handling requests to the steno app. """

    def __init__(self, app:StenoApplication, logger:Callable[[str], None]=print, **kwargs) -> None:
        super().__init__(**kwargs)
        self._app = app       # Main steno app.
        self._log = logger    # Callable to log all app exceptions.
        self._lock = Lock()   # Lock to protect the main app, which may not be thread-safe.

    def process(self, params:dict, *args) -> StenoGUIOutput:
        """ The decoded object is a params dict with the action, its arguments (if any), and all options.
            If an exception occurs, log it, then reraise to send a 500 error response. """
        with self._lock:
            try:
                action = params["action"]
                args = params["args"]
                options = params["options"]
                method = getattr(self._app, "gui_" + action)
                return method(*args, **options)
            except Exception:
                self._log('APP EXCEPTION\n' + format_exc())
                raise

    def add_data_class(self, data_cls:type) -> None:
        """ Add a conversion method for a data class, whose instance attributes may be encoded
            directly into a JSON object. This uses vars(), so objects without a __dict__ are not allowed.
            For this to work, each attribute must contain either a JSON-compatible type or another data class.
            Since type information is not encoded, this conversion is strictly one-way. """
        setattr(self, f"convert_{data_cls.__name__}", vars)


class SpectraHttp(Spectra):
    """ Run the Spectra HTTP web application. """

    # Standard HTTP configuration settings are command-line options.
    address: str = CmdlineOption("--http-addr", "", "IP address or hostname for server.")
    port: int = CmdlineOption("--http-port", 80, "TCP port to listen for connections.")
    directory: str = CmdlineOption("--http-dir", HTTP_PUBLIC_DEFAULT, "Root directory for public HTTP file service.")

    def build_server(self, app:StenoApplication, logger:Callable[[str], None]=print) -> HTTPServer:
        app_service = StenoAppService(app, logger)
        for cls in [DisplayData, DisplayPage, SearchResults, StenoGUIOutput]:
            app_service.add_data_class(cls)
        file_service = HTTPFileService(self.directory)
        post_router = HTTPPathRouter()
        post_router.add_route("/request", app_service)
        method_router = HTTPMethodRouter()
        method_router.add_route("GET", file_service)
        method_router.add_route("HEAD", file_service)
        method_router.add_route("POST", post_router)
        return HTTPServer(method_router, logger, threaded=True)

    def run(self) -> int:
        """ Build the app, start the server, and poll for connections indefinitely. """
        log = self.build_logger().log
        log("Loading...")
        app = self.build_app()
        self.load_app(app)
        server = self.build_server(app, log)
        log("Server started.")
        try:
            server.start(self.address, self.port)
        finally:
            server.shutdown()
        log("Server stopped.")
        return 0


http = SpectraHttp.main

if __name__ == '__main__':
    sys.exit(http())
