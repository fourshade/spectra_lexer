""" Main entry point for Spectra's HTTP application. """

import os

from .server import HTTPServer
from spectra_lexer.core import CmdlineOption
from spectra_lexer.view import ViewApplication, VIEW


class HttpApplication(ViewApplication, VIEW):
    """ Master component for HTTP operations. Controls the server application as a whole. """

    _HTTP_PUBLIC = os.path.join(os.path.split(__file__)[0], "public")

    address: str = CmdlineOption("http-addr", default="", desc="IP address or hostname for server.")
    port: int = CmdlineOption("http-port", default=80, desc="TCP port to listen for connections.")
    dir: str = CmdlineOption("http-dir", default=_HTTP_PUBLIC, desc="Root directory for public HTTP file service.")

    server: HTTPServer = None

    def _build_interface(self) -> list:
        """ Run the server on the main thread. """
        return []

    def run(self) -> int:
        """ Start the server and console and run them indefinitely. """
        self.server = HTTPServer(self.dir, self.VIEWAction, self.COREStatus)
        self.server.start(self.address, self.port)
        try:
            self.repl()
        finally:
            self.server.shutdown()
        return 0

    def VIEWActionResult(self, *args) -> None:
        """ Finish a response and send it to the client. """
        self.server.process_done(*args)
