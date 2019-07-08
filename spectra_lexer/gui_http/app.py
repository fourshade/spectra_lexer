""" Main entry point for Spectra's HTTP application. """

from .base import GUIHTTP
from spectra_lexer import gui_http
from spectra_lexer.view.app import ViewApplication


class HttpApplication(ViewApplication, GUIHTTP):
    """ Master component for HTTP operations. Controls the application as a whole. """

    DESCRIPTION = "Run the application as an HTTP web server."

    def _class_paths(self) -> list:
        """ Run the server on the main thread. """
        return [gui_http]

    def run(self) -> int:
        """ Start the server and run it indefinitely. """
        self.GUIHTTPServe()
        return 0


HttpApplication.set_entry_point("http")
