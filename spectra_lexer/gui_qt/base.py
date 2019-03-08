import sys
from typing import ClassVar, Sequence

from PyQt5.QtWidgets import QApplication

from spectra_lexer import Component
from spectra_lexer.gui_qt.main_window import MainWindow


class GUIQt(Component):
    """ Master component for GUI Qt operations. Controls the main window and application object. """

    # We can create the QApplication at class level since only one is ever allowed to run.
    qt_app: ClassVar[QApplication] = QApplication.instance() or QApplication(sys.argv)
    window: MainWindow = None  # Main window object.

    @on("start")
    def start(self, *, gui_menus:Sequence[str]=("File", "Tools"), **opts) -> None:
        """ Make the window, get the required widgets, and send them all to their required components. """
        window = self.window = MainWindow()
        # The menu must be initialized first so it can add items from other components.
        self.engine_call("new_gui_menu", window.widgets, gui_menus)
        self.engine_call("new_gui_window", window.widgets)
        self.engine_call("new_menu_item", "File", "Exit", "gui_window_close", sep_first=True)
        # Show the window, then manually process all GUI events to avoid hanging.
        window.show()
        self.qt_app.processEvents()

    @respond_to("run")
    def loop(self) -> int:
        """ Start the GUI event loop and run it indefinitely. """
        self.qt_app.exec_()
        return 1

    @on("gui_window_close")
    def close(self) -> None:
        """ Closing the main window kills the program in standalone mode. Do not call as a plugin. """
        if self.window is not None:
            self.window.close()
