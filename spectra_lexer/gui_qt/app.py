""" Main entry point for Spectra's interactive GUI application. """

import sys
from typing import Callable

from PyQt5.QtCore import pyqtSignal, QObject
from PyQt5.QtWidgets import QApplication

from spectra_lexer import gui_qt
from spectra_lexer.core import Runtime, ThreadedRuntime
from spectra_lexer.gui import GUIApplication


class _Connection(QObject):
    """ A simple signal-slot connection for transferring tuples between threads. """

    def __init__(self, callback:Callable):
        super().__init__()
        self.signal.connect(callback)

    def __call__(self, arg:tuple) -> None:
        """ This notifies the main thread when it needs to receive a command. """
        self.signal.emit(arg)

    # Signals
    signal = pyqtSignal(tuple)


class GUIQtApplication(GUIApplication):
    """ Master component for GUI Qt operations. Controls the application as a whole.
        To send commands to the GUI, the child engines send a Qt signal to the main engine. """

    # We can create the QApplication at class level since only one is ever allowed to run.
    QT_APP: QApplication = QApplication.instance() or QApplication(sys.argv)

    def _class_paths(self) -> list:
        """ Run the GUI on the main thread, and the standard steno components on a worker thread. """
        return [[gui_qt], super()._class_paths()]

    def _runtime(self) -> Runtime:
        return ThreadedRuntime(passthrough=_Connection)

    def event_loop(self) -> int:
        return self.QT_APP.exec_()
