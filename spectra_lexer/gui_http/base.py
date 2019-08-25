""" Main entry point for Spectra's HTTP application. """

import os
import sys
from threading import Lock, Thread
from typing import Any

from .http import BaseTCPServer, HTTPDispatcher, HTTPMethodTable, HTTPFileGetter, HTTPJSONProcessor
from spectra_lexer import Spectra
from spectra_lexer.app import StenoApplication, StenoOptions
from spectra_lexer.cmdline import Option
from spectra_lexer.console import SystemConsole


class HttpOptions(StenoOptions):
    """ Master component for HTTP operations. Controls the server application as a whole. """

    HTTP_PUBLIC = os.path.join(os.path.split(__file__)[0], "public")

    address: str = Option("--http-addr", "", "IP address or hostname for server.")
    port: str = Option("--http-port", 80, "TCP port to listen for connections.")
    directory: str = Option("--http-dir", HTTP_PUBLIC, "Root directory for public HTTP file service.")


class HTTPServer(BaseTCPServer):
    """ Class for threaded socket-based HTTP server. May be run directly as an entry point. """

    SERVER_VERSION = f"Spectra/0.1 Python/{sys.version.split()[0]}"

    app: StenoApplication

    _lock: Lock
    _dispatcher: HTTPDispatcher

    def __init__(self, opts:HttpOptions) -> None:
        """ The main app code may not be thread-safe. Make sure to log or process only one response at a time. """
        self.app = StenoApplication(opts)
        self._lock = Lock()
        fgetter = HTTPFileGetter(opts.directory)
        processor = HTTPJSONProcessor(self._locked_process_action)
        method_handler = HTTPMethodTable(GET=fgetter, HEAD=fgetter, POST=processor)
        self._dispatcher = HTTPDispatcher(method_handler, self.SERVER_VERSION, self._locked_log)
        # Start the console and server and poll for connections on a new thread indefinitely.
        Thread(target=self.start, args=(opts.address, opts.port), daemon=True).start()
        try:
            SystemConsole(vars(self)).repl()
        finally:
            self.shutdown()

    def __call__(self, *args) -> None:
        """ Handle each connection with a new thread. """
        Thread(target=self._dispatcher, args=args, daemon=True).start()

    def _locked_log(self, *args) -> Any:
        with self._lock:
            return self.app.log(*args)

    def _locked_process_action(self, state:dict, path:str, query:dict) -> dict:
        """ The decoded object is the state dict, and the relative path includes the action. """
        action = path.split('/')[-1]
        with self._lock:
            return self.app.process_action(state, action)


http = Spectra(HTTPServer, HttpOptions)
