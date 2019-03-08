import sys

from PyQt5.QtWidgets import QApplication

from spectra_lexer import Component
from .main_window import MainWindow


class GUIQt(Component):
    """ Master component for GUI Qt operations. Controls the main window and application object. """

    # We can create the QApplication at class level since only one is ever allowed to run.
    QT_APP: QApplication = QApplication.instance() or QApplication(sys.argv)
    GUI_MENUS = ["File", "Tools"]  # Menus available by default. Subclasses can add or remove these.

    window: MainWindow = None  # Main GUI window. Lifecycle determines that of the application.

    @on("start")
    def start(self) -> None:
        """ Make the window if necessary, get all required widgets from it, and send them to the components. """
        window = self.window = MainWindow()
        widgets = window.widgets
        # The menu must be initialized first so it can add items from other components.
        self.engine_call("new_gui_menu", widgets, self.GUI_MENUS)
        self.engine_call("new_gui_window", widgets)
        self.engine_call("new_menu_item", "File", "Exit", "gui_window_close", window, sep_first=True)
        # Show the window, then manually process all GUI events to avoid hanging.
        window.show()
        self.QT_APP.processEvents()

    @on("run")
    def run(self) -> int:
        """ If no subclasses object, start the GUI event loop and run it indefinitely. """
        return self.QT_APP.exec_()

    @on("gui_window_close")
    def close(self, window:MainWindow) -> None:
        """ Closing the main window kills the program in standalone mode. Do not call as a plugin. """
        if window is not None:
            window.close()
