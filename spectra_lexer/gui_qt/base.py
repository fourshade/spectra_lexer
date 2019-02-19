""" Base module for the GUI Qt package. """

from typing import Any

from spectra_lexer import Gateway
from spectra_lexer.gui_qt.board import GUIQtBoardDisplay
from spectra_lexer.gui_qt.config import GUIQtConfig
from spectra_lexer.gui_qt.console import GUIQtConsoleDisplay
from spectra_lexer.gui_qt.main_window import MainWindow
from spectra_lexer.gui_qt.menu import GUIQtMenu
from spectra_lexer.gui_qt.search import GUIQtSearch
from spectra_lexer.gui_qt.graph import GUIQtTextDisplay
from spectra_lexer.gui_qt.window import GUIQtWindow
from spectra_lexer.interactive import InteractiveApplication
from spectra_lexer.utils import nop

# Subcomponents of the GUI with their widget sections. Some components may use the same section.
COMPONENTS = {GUIQtMenu:           "menu",
              GUIQtSearch:         "search",
              GUIQtWindow:         "window",
              GUIQtConfig:         "window",
              GUIQtBoardDisplay:   "board",
              GUIQtTextDisplay:    "text",
              GUIQtConsoleDisplay: "text"}


class GUIQtGateway(Gateway):
    """ Central constructor/container for all Qt components. All commands issued to children go through here first. """

    ROLE = "gui"

    window: MainWindow              # Main window; must be publicly accessible for the Plover plugin.
    process_events: callable = nop  # Callback to handle GUI events after every engine call.

    def __init__(self):
        """ Create the main window and assemble all child components with their required widgets. """
        super().__init__()
        self.window = MainWindow()
        cmp_args = self.window.partition()
        self.components = [cls(*cmp_args[w]) for (cls, w) in COMPONENTS.items()]

    def engine_call(self, func, *args, **kwargs) -> Any:
        """ Manually process events after every engine call to avoid hanging. """
        value = func(*args, **kwargs)
        self.process_events()
        return value


class GUIQtApplication(InteractiveApplication):
    """ Class for operation of the Spectra program with the standard Qt GUI. """

    _gateway: GUIQtGateway  # Gateway reference for assigning the event handler and getting the main window.

    def __init__(self, *cls_iter:type, gui_evt_proc:callable=None):
        """ The Qt widgets take direct orders from the GUIQt gateway and its children. """
        super().__init__(GUIQtGateway, *cls_iter)
        self._gateway = next(c for c in self.components if isinstance(c, GUIQtGateway))
        # The QApplication instance is needed by the gateway to manually process GUI events.
        self._gateway.process_events = gui_evt_proc or nop

    def get_window(self) -> MainWindow:
        """ Return the main window instance to use in the Plover plugin entry point. """
        return self._gateway.window
