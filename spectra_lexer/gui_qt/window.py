from typing import Sequence

from PyQt5.QtWidgets import QApplication

from spectra_lexer import Component
from spectra_lexer.gui_qt.main_window import MainWindow


class GUIQtWindow(Component):
    """ Master component for GUI Qt operations. Controls the main window. """

    window: MainWindow = None  # Main window object.

    @on("start")
    def start(self, *, gui_menus:Sequence[str]=("File", "Tools"), **opts) -> None:
        # Make the window, get the required widgets, send them all to their required components, and show the window.
        qt_app = QApplication.instance()
        window = self.window = MainWindow()
        # The menu must be initialized first so it can add items from other components.
        self.engine_call("new_gui_menu", window.widgets, gui_menus)
        self.engine_call("new_gui_window", window.widgets)
        self.engine_call("new_menu_item", "File", "Exit", "gui_window_close", sep_first=True)
        window.show()
        # Manually process events after GUI setup to avoid hanging.
        qt_app.processEvents()

    @on("gui_window_close")
    def close(self) -> None:
        """ Closing the main window kills the program in standalone mode.
            It affects the entire QApplication, so this shouldn't be called while running as a plugin. """
        if self.window is not None:
            self.window.close()
