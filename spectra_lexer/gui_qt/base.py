import sys

from PyQt5.QtWidgets import QApplication

from .main_window import MainWindow
from spectra_lexer import Component


class GUIQt(Component):
    """ Master component for GUI Qt operations. Controls the main window and application objects. """

    # We can create the QApplication at class level since only one is ever allowed to run.
    QT_APP: QApplication = QApplication.instance() or QApplication(sys.argv)
    window: MainWindow = None  # Main GUI window. Lifecycle determines that of the application.

    @on("start")
    def start(self) -> None:
        """ Make the window, get all required widgets from it, send those to the components, and show it. """
        self.window = MainWindow()
        for group, widgets in self.window.widget_groups().items():
            self.engine_call(f"new_gui_{group}", *widgets)
        self.window.show()
        # Manually process all GUI events at the end to avoid hanging.
        self.QT_APP.processEvents()

    @on("run")
    def run(self) -> int:
        """ If no subclasses object, start the GUI event loop and run it indefinitely. """
        return self.QT_APP.exec_()

    @on("gui_window_close")
    def close(self) -> None:
        """ Closing the main window kills the program in standalone mode. Do not call as a plugin. """
        if self.window is not None:
            self.window.close()
