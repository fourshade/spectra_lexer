import os
from threading import Lock

from .http import HTTPFileGetter, HTTPJSONProcessor, HTTPMethodTable, HTTPServer
from spectra_lexer.app import StenoApplication, StenoMain
from spectra_lexer.option import CmdlineOption


class StenoAppProcessor(HTTPJSONProcessor):
    """ The main app code may not be thread-safe. This wrapper will process only one response at a time. """

    def __init__(self, app:StenoApplication, **kwargs) -> None:
        super().__init__(**kwargs)
        self._process = app.process_action
        self._lock = Lock()

    def process(self, state:dict, path:str, *args) -> dict:
        """ The decoded object is the state dict, and the relative path includes the action. """
        action = path.split('/')[-1]
        with self._lock:
            return self._process(state, action)


class HttpMain(StenoMain):
    """ Main entry point for Spectra's HTTP application. """

    HTTP_PUBLIC = os.path.join(os.path.split(__file__)[0], "public")

    address: str = CmdlineOption("--http-addr", "", "IP address or hostname for server.")
    port: int = CmdlineOption("--http-port", 80, "TCP port to listen for connections.")
    directory: str = CmdlineOption("--http-dir", HTTP_PUBLIC, "Root directory for public HTTP file service.")

    def main(self) -> int:
        """ Start the server and poll for connections indefinitely. """
        log = self.build_logger().log
        log("Loading...")
        app = self.build_app()
        processor = StenoAppProcessor(app)
        fgetter = HTTPFileGetter(self.directory)
        method_handler = HTTPMethodTable(GET=fgetter, HEAD=fgetter, POST=processor)
        server = HTTPServer(method_handler, log, threaded=True)
        log("Server started.")
        try:
            server.start(self.address, self.port)
        finally:
            server.shutdown()
        log("Server stopped.")
        return 0


http = HttpMain()
