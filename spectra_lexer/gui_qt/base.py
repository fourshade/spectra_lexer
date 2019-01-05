""" Base module for the GUI Qt package. Includes the main component. """

from typing import List

from spectra_lexer import SpectraComponent
from spectra_lexer.gui_qt.board import GUIQtBoardDisplay
from spectra_lexer.gui_qt.main_window import MainWindow
from spectra_lexer.gui_qt.menu import GUIQtMenu
from spectra_lexer.gui_qt.search import GUIQtSearch
from spectra_lexer.gui_qt.text import GUIQtTextDisplay
from spectra_lexer.gui_qt.window import GUIQtWindow

# Constituent components of the GUI. The window shouldn't be shown until everything else is set up, so connect it last.
GUI_COMPONENTS = [("menu",   GUIQtMenu),
                  ("search", GUIQtSearch),
                  ("text",   GUIQtTextDisplay),
                  ("board",  GUIQtBoardDisplay),
                  ("window", GUIQtWindow)]


class GUIQt(SpectraComponent):
    """ Component container for the GUI. It isn't a proper component; all commands and callbacks
        are routed to/from its child components, but the engine can't tell the difference. """

    window: MainWindow
    children: List[SpectraComponent]

    def __init__(self):
        self.window = MainWindow()
        cmp_args = self.window.partition()
        self.children = [tp(*cmp_args[k]) for (k, tp) in GUI_COMPONENTS]

    def commands(self) -> list:
        return [i for c in self.children for i in c.commands()]

    def set_engine_callback(self, *args) -> None:
        for c in self.children:
            c.set_engine_callback(*args)

    def configure(self, **cfg_dict) -> None:
        for c in self.children:
            c.configure(**cfg_dict)
