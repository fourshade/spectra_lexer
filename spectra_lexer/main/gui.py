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

    def __init__(self, main_classes=(), worker_classes=()):
        """ Run the GUI on the main thread, and the standard steno components on a worker thread. """
        classes = [gui_qt, *main_classes], [core, steno, tools, *worker_classes]
        # To send commands to the GUI, the child engines send a Qt signal that activates call_main().
        super().__init__(*classes, parent_send=Connection(self.call_main).send)

    def run(self, *args) -> int:
        """ Start the GUI event loop and run it indefinitely. Record uncaught exceptions before quitting. """
        try:
            return self.QT_APP.exec_()
        except Exception as e:
            self.handle_exception(e)
            return -1
