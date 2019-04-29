""" Main module and entry point for Spectra's interactive GUI application. """

import sys

from PyQt5.QtCore import pyqtSignal, QObject
from PyQt5.QtWidgets import QApplication

from spectra_lexer import gui_qt
from spectra_lexer.gui import GUIApplication


class _Connection(QObject):
    """ A simple signal-slot connection for transferring tuples between threads. """

    def __init__(self, callback):
        super().__init__()
        self.signal.connect(callback)

    def __call__(self, arg:tuple) -> None:
        self.signal.emit(arg)

    # Signals
    signal = pyqtSignal(tuple)


class GUIQtApplication(GUIApplication):
    """ Master component for GUI Qt operations. Controls the application as a whole.
        Runs the GUI on the main thread, and the standard steno components on a worker thread.
        To send commands to the GUI, the child engines send a Qt signal to the main engine. """

    CLASS_PATHS = [gui_qt]
    PASSTHROUGH = _Connection

    # We can create the QApplication at class level since only one is ever allowed to run.
    QT_APP: QApplication = QApplication.instance() or QApplication(sys.argv)

    def event_loop(self):
        return self.QT_APP.exec_()
