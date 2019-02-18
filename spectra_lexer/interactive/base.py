""" Base module for the interactive GUI package. """

from spectra_lexer import Composite
from spectra_lexer.interactive.board import BoardRenderer
from spectra_lexer.interactive.console import SpectraConsole
from spectra_lexer.interactive.graph import GraphRenderer
from spectra_lexer.interactive.search import SearchEngine
from spectra_lexer.interactive.svg import SVGManager


class Interactive(Composite):
    """ Central constructor/container for all components designed for user interaction logic. """

    ROLE = "user"

    def __init__(self):
        """ Components specifically for user interaction. Without a GUI, these components do no good. """
        super().__init__(SearchEngine,
                         SVGManager,
                         BoardRenderer,
                         GraphRenderer,
                         SpectraConsole)
