""" Main entry point for Spectra's interactive GUI application. """

import sys

from PyQt5.QtWidgets import QApplication

from .engine import AsyncWrapper
from .ext import QtGUIExtension
from .window import QtGUI
from spectra_lexer import StenoApplication


class QtApplication(StenoApplication):
    """ Master component for GUI Qt operations. Controls the application as a whole. """

    gui: QtGUI
    gui_ext: QtGUIExtension

    def load(self) -> None:
        """ Wrap the main steno engine to operate asynchronously on a new thread to avoid blocking the GUI. """
        self.steno = AsyncWrapper(self.steno, self.exception)
        self.gui = self["gui"] = QtGUI(self.steno.VIEWAction)
        self.gui_ext = self["gui_ext"] = QtGUIExtension(self.gui, self.steno, self.system)
        self.show()
        self.check_index()
        super().load()

    def check_index(self) -> None:
        """ If there is no index file on first start, tell the GUI so it can send up a dialog. """
        if not self.system.file_exists(self.index_file):
            self.gui_ext.index_missing()

    def show(self) -> None:
        """ For a plugin window, this is called by its host application to re-open it after closing. """
        self.gui.show()

    def close(self) -> None:
        """ Closing the main window should kill the program in standalone mode, but not as a plugin. """
        self.gui.close()

    def status(self, status:str) -> None:
        super().status(status)
        self.gui.status(status)

    def exception(self, exc:Exception) -> None:
        tb_text = self.system.log_exception(exc)
        self.gui.exc_traceback(tb_text)


def gui(*argv:str) -> int:
    """ Standalone GUI Qt application entry point. Requires a QApplication to be created before init.
        After everything is loaded, start a GUI event loop and run it indefinitely. """
    qt_app = QApplication(sys.argv)
    QtApplication(*argv)
    return qt_app.exec_()
