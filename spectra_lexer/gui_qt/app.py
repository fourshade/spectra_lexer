""" Main entry point for Spectra's interactive GUI application. """

import sys
from typing import Callable

from PyQt5.QtCore import pyqtSignal, QObject
from PyQt5.QtWidgets import QApplication

from .ext import QtGUIExtension
from .window import MainWindow
from spectra_lexer.app import StenoApplication


class _Connection(QObject):
    """ A simple signal-slot connection for transferring tuples to the main thread. """

    def __init__(self, callback:Callable):
        # A passthrough function may notify the main thread when it needs to run a command on the GUI.
        # To send commands to the GUI, the child threads send a Qt signal to the main thread.
        super().__init__()
        self.signal.connect(callback)

    def __call__(self, arg:tuple) -> None:
        """ This notifies the main thread when it needs to receive a command. """
        self.signal.emit(arg)

    # Signals
    signal = pyqtSignal(tuple)


class QtApplication(StenoApplication):
    """ Master component for GUI Qt operations. Controls the application as a whole. """

    window: MainWindow
    gui_ext: QtGUIExtension
    _qt_app: QApplication

    def load(self) -> None:
        """ Create the QApplication only on init to avoid interference with Plover. """
        self._qt_app = QApplication.instance() or QApplication(sys.argv)
        self.window = self["window"] = MainWindow(self.steno.VIEWAction)
        self.gui_ext = self["gui_ext"] = QtGUIExtension(self.window, self.steno, self.system)
        super().load()
        self.check_index()

    def check_index(self) -> None:
        """ If there is no index file on first start, tell the GUI so it can send up a dialog. """
        if not self.system.file_exists(self.index_file):
            self.gui_ext.index_missing()

    # def check_config(self) -> None:
    #     self.view.config_info(config.info())

    def loop(self) -> int:
        """ Start a GUI event loop and run it indefinitely. """
        return self._qt_app.exec_()

    def status(self, status:str) -> None:
        super().status(status)
        self.window.status(status)

    def exc_traceback(self, tb_text:str) -> None:
        super().exc_traceback(tb_text)
        self.window.exc_traceback(tb_text)


class StenoGUIApplication(QtApplication):
    """ Standalone GUI Qt application class. """

    def run(self) -> int:
        """ Start the event loop after setup. """
        return self.loop()
