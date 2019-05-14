""" Main entry point for Spectra's interactive GUI application. """

import sys
from traceback import print_exc
from typing import Callable

from PyQt5.QtCore import pyqtSignal, QObject
from PyQt5.QtWidgets import QApplication

from spectra_lexer import gui_qt, view
from spectra_lexer.core.engine import ThreadedEngine
from spectra_lexer.core.group import ComponentGroup
from spectra_lexer.steno.app import StenoApplication


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


class GUIQtApplication(StenoApplication):
    """ Master component for GUI Qt operations. Controls the application as a whole. """

    # We can create the QApplication at class level since only one is ever allowed to run.
    QT_APP: QApplication = QApplication.instance() or QApplication(sys.argv)

    def __init__(self):
        """ Send the main start signal as the last step before the event loop. """
        super().__init__()
        super().run()

    def _class_paths(self) -> list:
        """ Run the GUI on the main thread, and the other layers on worker threads. """
        return [[gui_qt], [view, *super()._class_paths()]]

    def _engine(self, components:ComponentGroup) -> Callable:
        """ We use multiple threads to avoid overwhelming the main GUI thread with heavy computations.
            To send commands to the GUI, the child threads send a Qt signal to the main thread. """
        return ThreadedEngine.group(components.split(), passthrough=_Connection)

    def run(self) -> int:
        """ Start the GUI event loop and run it indefinitely. Print uncaught exceptions before quitting. """
        try:
            return self.QT_APP.exec_()
        except Exception:
            print_exc()
            return -1


if __name__ == '__main__':
    sys.exit(GUIQtApplication().run())
