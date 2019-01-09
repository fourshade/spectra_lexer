""" Base module for the GUI Qt package. """

from spectra_lexer import Composite
from spectra_lexer.gui_qt.board import GUIQtBoardDisplay
from spectra_lexer.gui_qt.config import GUIQtConfig
from spectra_lexer.gui_qt.main_window import MainWindow
from spectra_lexer.gui_qt.menu import GUIQtMenu
from spectra_lexer.gui_qt.search import GUIQtSearch
from spectra_lexer.gui_qt.text import GUIQtTextDisplay
from spectra_lexer.gui_qt.window import GUIQtWindow

# Constituent components of the GUI and their widget sections. Some components may use the same section.
# The window shouldn't be shown until everything else is set up, so create the window controller last.
GUI_COMPONENTS = [(GUIQtMenu,         "menu"),
                  (GUIQtSearch,       "search"),
                  (GUIQtTextDisplay,  "text"),
                  (GUIQtBoardDisplay, "board"),
                  (GUIQtConfig,       "window"),
                  (GUIQtWindow,       "window")]


class GUIQt(Composite):
    """ Top-level component of the GUI Qt package. Central constructor/container for all other GUI components. """

    window: MainWindow  # Main window must be publicly accessible for the Plover plugin.

    def __init__(self):
        """ Assemble child components before the engine starts. """
        self.window = MainWindow()
        cmp_args = self.window.partition()
        self.set_children([tp(*cmp_args[w]) for (tp, w) in GUI_COMPONENTS])
