from typing import Callable, Dict

from PyQt5.QtWidgets import QFileDialog, QMainWindow, QDialog

from .config_dialog import ConfigDialog
from spectra_lexer import Component


class GUIQtWindow(Component):
    """ Controls the GUI Qt window itself and creates dialogs from it. """

    window: QMainWindow = None  # Main window object. Must be the parent of any new dialogs.
    dialogs: Dict[str, QDialog]  # Dialog object tracker. Each one should persist when closed/hidden.

    def __init__(self):
        super().__init__()
        self.dialogs = {}

    @on("new_gui_window")
    def new_gui(self, window:QMainWindow) -> None:
        """ Save the main window and show it. """
        self.window = window
        window.show()

    @on("gui_window_file_dialog")
    def file_dialog(self, *args) -> tuple:
        return QFileDialog.getOpenFileNames(self.window, *args)

    @on("gui_window_config_dialog")
    def config_dialog(self, on_accept_cb:Callable, *args) -> QDialog:
        """ Create GUI configuration manager dialog; allows editing of config values for any component. """
        if "config" not in self.dialogs:
            self.dialogs["config"] = ConfigDialog(self.window, on_accept_cb, *args)
        return self.dialogs["config"]

    @on("gui_window_close")
    def close(self) -> None:
        """ Closing the main window kills the program in standalone mode. Do not call as a plugin. """
        if self.window is not None:
            self.window.close()
