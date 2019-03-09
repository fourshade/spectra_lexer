import sys

from PyQt5.QtWidgets import QApplication

from spectra_lexer import Component
from .main_window import MainWindow


class GUIQt(Component):
    """ Master component for GUI Qt operations. Controls the main window and application object. """

    # We can create the QApplication at class level since only one is ever allowed to run.
    QT_APP: QApplication = QApplication.instance() or QApplication(sys.argv)
    window: MainWindow = None  # Main GUI window. Lifecycle determines that of the application.

    @on("start")
    def start(self) -> None:
        """ Make the window if necessary, get all required widgets from it, and send them to the components. """
        self.window = MainWindow()
        for group, widgets in self.window.widget_groups().items():
            self.engine_call(f"new_gui_{group}", *widgets)
        # Show the window, then manually process all GUI events to avoid hanging.
        self.window.show()
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
