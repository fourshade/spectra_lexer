""" Main entry point for Spectra's interactive GUI application. """

import sys
from typing import Callable

from PyQt5.QtCore import pyqtSignal, QObject
from PyQt5.QtWidgets import QApplication

from .base import GUIQT
from spectra_lexer import gui_qt
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


class QtApplication(ViewApplication, GUIQT):
    """ Master component for GUI Qt operations. Controls the application as a whole. """

    DESCRIPTION = "Run the application as a standalone GUI."

    # We can create the QApplication at class level since only one is ever allowed to run.
    QT_APP: QApplication = QApplication.instance() or QApplication(sys.argv)

    def _main_class_paths(self) -> list:
        """ Run the GUI on the main thread. """
        return [gui_qt]

    def _engine(self, **kwargs):
        """ To send commands to the GUI, the child threads send a Qt signal to the main thread. """
        return super()._engine(passthrough=_Connection, **kwargs)

    def run(self) -> int:
        """ Start the GUI event loop and run it indefinitely. The full component list is useful for debugging. """
        self.ALL_COMPONENTS = list(self._components.recurse_items())
        return self.QT_APP.exec_()


# With no mode arguments, the standalone GUI app is run by default.
QtApplication.set_entry_point("gui", is_default=True)
