import sys

from PyQt5.QtWidgets import QApplication

from .base import Application
from spectra_lexer import core, gui_qt, steno, tools


class GUIQtApplication(Application):
    """ Master component for GUI Qt operations. Controls the application as a whole. """

    # We can create the QApplication at class level since only one is ever allowed to run.
    QT_APP: QApplication = QApplication.instance() or QApplication(sys.argv)

    def __init__(self, *classes):
        super().__init__(core, steno, gui_qt, tools, *classes)

    def load_resources(self) -> None:
        """ Load the window and manually process all GUI events before doing file I/O to avoid hanging. """
        self.call("gui_window_load")
        self.QT_APP.processEvents()
        super().load_resources()

    def run(self, *args) -> int:
        """ If no subclasses object, start the GUI event loop and run it indefinitely. """
        self.call("gui_set_enabled", True)
        return self.QT_APP.exec_()
