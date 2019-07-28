""" Main entry point for Spectra's interactive GUI application. """

import sys
from typing import Callable

from PyQt5.QtCore import pyqtSignal, QObject
from PyQt5.QtWidgets import QApplication

from .tools import QtTools
from .view import QtView
from .window import QtWindow
from spectra_lexer.view.app import ViewApplication


class _Connection(QObject):
    """ A simple signal-slot connection for transferring tuples to the main thread. """

    def __init__(self, callback:Callable):
        super().__init__()
        self.signal.connect(callback)

    def __call__(self, arg:tuple) -> None:
        """ This notifies the main thread when it needs to receive a command. """
        self.signal.emit(arg)

    # Signals
    signal = pyqtSignal(tuple)


class QtApplication(ViewApplication):
    """ Master component for GUI Qt operations. Controls the application as a whole. """

    qt_app: QApplication = None

    def _build_components(self) -> list:
        """ Run the GUI on the main thread. """
        return [QtWindow(), QtView(), QtTools()]

    def _build_engine(self, *args, **kwargs):
        """ To send commands to the GUI, the child threads send a Qt signal to the main thread.
            Create the QApplication at engine build to avoid interference with Plover. """
        self.qt_app = QApplication.instance() or QApplication(sys.argv)
        return super()._build_engine(*args, passthrough=_Connection, **kwargs)

    def run(self) -> int:
        """ Start the GUI event loop and run it indefinitely. """
        return self.qt_app.exec_()
