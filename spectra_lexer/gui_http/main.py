import os
import sys
from threading import Lock
from traceback import format_exc
from typing import Callable

from .http import HTTPFileService, HTTPJSONService, HTTPMethodRouter, HTTPPathRouter, HTTPServer
from spectra_lexer.app import StenoApplication
from spectra_lexer.base import StenoAppFactory, StenoAppOptions
from spectra_lexer.cmdline import CmdlineOption
from spectra_lexer.steno import SearchResults, StenoAnalysis, StenoAnalysisPage, StenoGUIOutput


class StenoAppService(HTTPJSONService):
    """ Main HTTP service for handling requests to the steno app. """

    def __init__(self, app:StenoApplication, log:Callable[[str], None]=print, **kwargs) -> None:
        super().__init__(**kwargs)
        self._app = app       # Main steno app.
        self._log = log       # Callable to log all app exceptions.
        self._lock = Lock()   # Lock to protect the main app, which may not be thread-safe.

    def process(self, params:dict, *args) -> dict:
        """ The decoded object is a params dict with the action, its arguments (if any), and all options.
            If an exception occurs, log it, then reraise to send a 500 error response. """
        with self._lock:
            try:
                return self._app.process_action(params["action"],
                                                *params["args"],
                                                **params["options"])
            except Exception:
                self._log('APP EXCEPTION\n' + format_exc())
                raise

    def convert_bytes(self, obj:bytes) -> str:
        """ Encode XML steno board bytes data as a string with the current encoding. """
        return obj.decode(self.encoding)

    def add_data_class(self, data_cls:type) -> None:
        """ Add a conversion method for a data class, whose instance attributes may be encoded
            directly into a JSON object. This uses vars(), so objects without a __dict__ are not allowed.
            For this to work, each attribute must contain either a JSON-compatible type or another data class.
            Since type information is not encoded, this conversion is strictly one-way. """
        setattr(self, f"convert_{data_cls.__name__}", vars)


class HttpAppOptions(StenoAppOptions):

    HTTP_PUBLIC_DEFAULT = os.path.join(os.path.split(__file__)[0], "public")

    address: str = CmdlineOption("--http-addr", "", "IP address or hostname for server.")
    port: int = CmdlineOption("--http-port", 80, "TCP port to listen for connections.")
    directory: str = CmdlineOption("--http-dir", HTTP_PUBLIC_DEFAULT, "Root directory for public HTTP file service.")


def http() -> int:
    """ Run the Spectra HTTP web application. """
    options = HttpAppOptions(__doc__)
    options.parse()
    factory = StenoAppFactory(options)
    log = factory.build_logger().log
    log("Loading...")
    app = factory.build_app()
    app_service = StenoAppService(app, log)
    for cls in [SearchResults, StenoAnalysis, StenoAnalysisPage, StenoGUIOutput]:
        app_service.add_data_class(cls)
    file_service = HTTPFileService(options.directory)
    post_router = HTTPPathRouter()
    post_router.add_route("/request", app_service)
    method_router = HTTPMethodRouter()
    method_router.add_route("GET", file_service)
    method_router.add_route("HEAD", file_service)
    method_router.add_route("POST", post_router)
    server = HTTPServer(method_router, log, threaded=True)
    # Start the server and poll for connections indefinitely.
    log("Server started.")
    try:
        server.start(options.address, options.port)
    finally:
        server.shutdown()
    log("Server stopped.")
    return 0


if __name__ == '__main__':
    sys.exit(http())
