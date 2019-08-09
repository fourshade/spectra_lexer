""" Main entry point for Spectra's HTTP application. """

import os

from .server import HTTPServer
from spectra_lexer import StenoApplication
from spectra_lexer.cmdline import CmdlineOption


class HttpApplication(StenoApplication):
    """ Master component for HTTP operations. Controls the server application as a whole. """

    _HTTP_PUBLIC = os.path.join(os.path.split(__file__)[0], "public")

    address: str = CmdlineOption("http-addr", default="", desc="IP address or hostname for server.")
    port: int = CmdlineOption("http-port", default=80, desc="TCP port to listen for connections.")
    dir: str = CmdlineOption("http-dir", default=_HTTP_PUBLIC, desc="Root directory for public HTTP file service.")

    server: HTTPServer

    def __init__(self, *argv:str):
        super().__init__(*argv)
        self.server = self["server"] = HTTPServer(self.dir, self.steno.VIEWAction, self.status)

    def run(self) -> int:
        """ Start the server and console and run them indefinitely. """
        self.server.start(self.address, self.port)
        try:
            self.repl()
        finally:
            self.server.shutdown()
        return 0


def http(*argv:str) -> int:
    app = HttpApplication(*argv)
    return app.run()
