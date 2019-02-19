""" Base module for the interactive GUI package. """

from spectra_lexer.core import CoreApplication
from spectra_lexer.interactive.board import BoardRenderer
from spectra_lexer.interactive.console import SpectraConsole
from spectra_lexer.interactive.graph import GraphRenderer
from spectra_lexer.interactive.search import SearchEngine
from spectra_lexer.interactive.svg import SVGManager


class InteractiveApplication(CoreApplication):
    """ Class for operation of the Spectra program in interactive mode using a GUI. """

    def __init__(self, *cls_iter:type):
        """ Components specifically for user interaction. Without a GUI, these components do no good. """
        super().__init__(SearchEngine,
                         SVGManager,
                         BoardRenderer,
                         GraphRenderer,
                         SpectraConsole, *cls_iter)

    def start(self, **opts) -> None:
        """ Load the board SVG asset and add the app and its components to the console on startup. """
        cvars = {"app": self, **{c.ROLE: c for c in self.components}}
        all_opts = {"svg": (), "console_vars": cvars, **opts}
        super().start(**all_opts)
