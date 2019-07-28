""" Main entry point for Spectra's HTTP application. """

from threading import Thread

from .base import GUIHTTP
from .server import HttpServer
from spectra_lexer.system import SYS
from spectra_lexer.view.app import ViewApplication


class HttpApplication(ViewApplication, SYS, GUIHTTP):
    """ Master component for HTTP operations. Controls the server application as a whole. """

    _done: bool = False

    def _build_components(self) -> list:
        """ Run the server on the main thread. """
        return [HttpServer()]

    def run(self) -> int:
        """ Start the server and console and run them indefinitely. """
        Thread(target=self.repl, daemon=True).start()
        while not self._done:
            self.GUIHTTPServe()
        self.GUIHTTPShutdown()
        return 0

    def repl(self) -> None:
        """ Open the console with stdin on a new thread. Shut down the server when finished. """
        self.SYSConsoleOpen()
        while True:
            text = input()
            if text.startswith("exit()"):
                break
            self.SYSConsoleInput(text)
        self._done = True
