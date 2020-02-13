""" Main module for the HTTP web application. """

import os
import sys
from threading import Lock

from spectra_lexer.app import StenoApplication, StenoGUIOutput
from spectra_lexer.base import Spectra
from spectra_lexer.display import DisplayData, DisplayPage
from spectra_lexer.http.connect import HTTPConnectionHandler
from spectra_lexer.http.service import HTTPDataService, HTTPFileService, HTTPGzipFilter, \
    HTTPContentTypeRouter, HTTPMethodRouter, HTTPPathRouter
from spectra_lexer.http.tcp import ThreadedTCPServer
from spectra_lexer.search import SearchResults
from spectra_lexer.util.cmdline import CmdlineOption
from spectra_lexer.util.json import CustomJSONEncoder, RestrictedJSONDecoder

JSON_DATA_CLASSES = [DisplayData, DisplayPage, SearchResults, StenoGUIOutput]
HTTP_PUBLIC_DEFAULT = os.path.join(os.path.split(__file__)[0], "http_public")


class StenoDataService(HTTPDataService):
    """ Main HTTP service for handling JSON requests to the steno app. """

    output_type = "application/json"

    def __init__(self, app:StenoApplication, decoder:RestrictedJSONDecoder, encoder:CustomJSONEncoder) -> None:
        self._app = app          # Main steno app.
        self._decoder = decoder  # JSON decoder with client restrictions.
        self._encoder = encoder  # JSON encoder with custom encoding methods for Python objects.
        self._lock = Lock()      # Lock to protect the codecs and main app, which may not be thread-safe.

    def process(self, data:bytes) -> bytes:
        """ Decode JSON input data into a params dict, process it, and return the output in JSON form. """
        str_in = data.decode('utf-8')
        with self._lock:
            params = self._decoder.decode(str_in)
            output = self._app_call(**params)
            str_out = self._encoder.encode(output)
        data_out = str_out.encode('utf-8')
        return data_out

    def _app_call(self, *, action:str, args:list, options:dict) -> StenoGUIOutput:
        """ Process a GUI app call. Input data includes a GUI action, its arguments (if any), and all options. """
        method = getattr(self._app, "gui_" + action)
        return method(*args, **options)


class SpectraHttp(Spectra):
    """ Run the Spectra HTTP web application. """

    # Standard HTTP configuration settings are command-line options.
    address: str = CmdlineOption("--http-addr", "", "IP address or hostname for server.")
    port: int = CmdlineOption("--http-port", 80, "TCP port to listen for connections.")
    directory: str = CmdlineOption("--http-dir", HTTP_PUBLIC_DEFAULT, "Root directory for public HTTP file service.")

    def build_data_service(self) -> StenoDataService:
        app = self.build_app()
        self.load_app(app)
        decoder = RestrictedJSONDecoder(size_limit=100000, obj_limit=20, arr_limit=20)
        encoder = CustomJSONEncoder()
        for cls in JSON_DATA_CLASSES:
            encoder.add_data_class(cls)
        return StenoDataService(app, decoder, encoder)

    def build_dispatcher(self, *args) -> HTTPConnectionHandler:
        file_service = HTTPFileService(self.directory)
        data_service = self.build_data_service()
        compressed_service = HTTPGzipFilter(data_service, size_threshold=1000)
        type_router = HTTPContentTypeRouter()
        type_router.add_route("application/json", compressed_service)
        post_router = HTTPPathRouter()
        post_router.add_route("/request", type_router)
        method_router = HTTPMethodRouter()
        method_router.add_route("GET", file_service)
        method_router.add_route("HEAD", file_service)
        method_router.add_route("POST", post_router)
        return HTTPConnectionHandler(method_router, *args)

    def run(self) -> int:
        """ Build the app, start the server, and poll for connections indefinitely. """
        log = self.build_logger().log
        log("Loading...")
        dispatcher = self.build_dispatcher(log)
        server = ThreadedTCPServer(dispatcher)
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
