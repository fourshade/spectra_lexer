""" Main module and entry point for Spectra's interactive GUI application. """

import sys

from PyQt5.QtCore import pyqtSignal, QObject
from PyQt5.QtWidgets import QApplication

from .app import ThreadedApplication
from spectra_lexer import core, gui_qt, steno, tools


class Connection(QObject):
    """ A simple signal-slot connection for transferring tuples between threads. """

    def __init__(self, callback):
        super().__init__()
        self.signal.connect(callback)

    def send(self, arg:tuple) -> None:
        self.signal.emit(arg)

    # Signals
    signal = pyqtSignal(tuple)


class GUIQtApplication(ThreadedApplication):
    """ Master component for GUI Qt operations. Controls the application as a whole. """

    # We can create the QApplication at class level since only one is ever allowed to run.
    QT_APP: QApplication = QApplication.instance() or QApplication(sys.argv)

    def __init__(self, *classes):
        """ To send commands to the GUI, the child engines send a simple Qt signal that activates main_call(). """
        super().__init__([gui_qt, tools], [core, steno, *classes], parent_send=Connection(self.main_call).send)

    def load(self, **options) -> None:
        """ The GUI components must start first to initialize the window and widgets before others use them. """
        self.call("gui_start", **options)
        self.call("gui_window_show")
        super().load(**options)

    def run(self, *args) -> int:
        """ If no subclasses object, start the GUI event loop and run it indefinitely. """
        return self.QT_APP.exec_()
