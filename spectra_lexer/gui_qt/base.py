""" Base module for the GUI Qt package. """

from typing import Any

from PyQt5.QtWidgets import QApplication

from spectra_lexer import Subprocess
from spectra_lexer.gui_qt.board import GUIQtBoardDisplay
from spectra_lexer.gui_qt.config import GUIQtConfig
from spectra_lexer.gui_qt.console import GUIQtConsoleDisplay
from spectra_lexer.gui_qt.main_window import MainWindow
from spectra_lexer.gui_qt.menu import GUIQtMenu
from spectra_lexer.gui_qt.search import GUIQtSearch
from spectra_lexer.gui_qt.graph import GUIQtTextDisplay
from spectra_lexer.gui_qt.window import GUIQtWindow

# Subcomponents of the GUI with their widget sections. Some components may use the same section.
COMPONENTS = {GUIQtMenu:           "menu",
              GUIQtSearch:         "search",
              GUIQtWindow:         "window",
              GUIQtConfig:         "window",
              GUIQtBoardDisplay:   "board",
              GUIQtTextDisplay:    "text",
              GUIQtConsoleDisplay: "text"}


class GUIQt(Subprocess):
    """ Top-level component of the GUI Qt package. Central constructor/container for all other Qt-based components. """

    ROLE = "gui"

    window: MainWindow        # Main window; must be publicly accessible for the Plover plugin.
    process_events: callable  # Callback to handle GUI events after every engine call.

    def __init__(self):
        """ Create the main window and assemble all child components with their required widgets. """
        self.window = MainWindow()
        cmp_args = self.window.partition()
        super().__init__(*COMPONENTS, args_iter=[cmp_args[w] for w in COMPONENTS.values()])
        self.process_events = QApplication.instance().processEvents

    def call(self, *args, **kwargs) -> Any:
        """ Manually process events after every engine call to avoid hanging. """
        value = super().call(*args, **kwargs)
        self.process_events()
        return value
