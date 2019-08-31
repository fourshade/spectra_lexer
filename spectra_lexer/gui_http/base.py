import os
import sys
from threading import Lock, Thread

from .http import BaseTCPServer, HTTPDispatcher, HTTPFileGetter, HTTPJSONProcessor, HTTPMethodTable
from spectra_lexer import Spectra
from spectra_lexer.app import StenoApplication, StenoMain
from spectra_lexer.console import SystemConsole
from spectra_lexer.log import StreamLogger
from spectra_lexer.option import CmdlineOption


class StenoAppProcessor(HTTPJSONProcessor):
    """ The main app code may not be thread-safe. This wrapper will log or process only one response at a time. """

    def __init__(self, app:StenoApplication, logger:StreamLogger, **kwargs) -> None:
        super().__init__(**kwargs)
        self._app = app
        self._logger = logger
        self._lock = Lock()

    def log(self, message:str) -> None:
        with self._lock:
            self._logger.log(message)

    def process(self, state:dict, path:str, *args) -> dict:
        """ The decoded object is the state dict, and the relative path includes the action. """
        action = path.split('/')[-1]
        with self._lock:
            return self._app.process_action(state, action)


class HTTPServer(BaseTCPServer):
    """ Class for threaded socket-based HTTP server. """

    def __init__(self, dispatcher:HTTPDispatcher) -> None:
        self._dispatcher = dispatcher

    def __call__(self, *args) -> None:
        """ Handle each connection with a new thread. """
        Thread(target=self._dispatcher, args=args, daemon=True).start()

    def run(self, *args) -> None:
        """ Start the console and server and poll for connections on a new thread indefinitely. """
        Thread(target=self.start, args=args, daemon=True).start()
        try:
            SystemConsole(vars(self)).repl()
        finally:
            self.shutdown()


class HttpMain(StenoMain):
    """ Main entry point for Spectra's HTTP application. """

    HTTP_PUBLIC = os.path.join(os.path.split(__file__)[0], "public")
    SERVER_VERSION = f"Spectra/0.1 Python/{sys.version.split()[0]}"

    address: str = CmdlineOption("--http-addr", "", "IP address or hostname for server.")
    port: str = CmdlineOption("--http-port", 80, "TCP port to listen for connections.")
    directory: str = CmdlineOption("--http-dir", HTTP_PUBLIC, "Root directory for public HTTP file service.")

    def main(self) -> int:
        logger = self.build_logger()
        logger.log("Loading...")
        app = self.build_app()
        processor = StenoAppProcessor(app, logger)
        fgetter = HTTPFileGetter(self.directory)
        method_handler = HTTPMethodTable(GET=fgetter, HEAD=fgetter, POST=processor)
        dispatcher = HTTPDispatcher(method_handler, self.SERVER_VERSION, processor.log)
        server = HTTPServer(dispatcher)
        logger.log("Server started.")
        server.run(self.address, self.port)
        return 0


http = Spectra(HttpMain)
