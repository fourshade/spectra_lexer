from functools import partial
from typing import Dict

from PyQt5.QtWidgets import QFileDialog, QMainWindow, QWidget

from spectra_lexer import Component, on
from spectra_lexer.gui_qt.dialog.config_dialog import ConfigDialog


class GUIQtDialogManager(Component):
    """ GUI dialog manager dialog; allows editing of config values for any component. """

    ROLE = "gui_dialog"

    window: QMainWindow = None   # Main window object. Must be the parent of any new dialogs.
    dialog: ConfigDialog = None  # Config dialog object. Should persist when closed/hidden.

    @on("new_gui_window")
    def start(self, widgets:Dict[str, QWidget]) -> None:
        """ Get the required widget. """
        self.window = widgets["window"][0]

    @on("new_config_dialog")
    def config_dialog(self, cfg_info:Dict[str, dict]) -> None:
        """ Create GUI configuration manager dialog; allows editing of config values for any component. """
        if self.dialog is None:
            self.dialog = ConfigDialog(self.window, partial(self.engine_call, "config_save"))
        # Load all supported config info for the current components into the dialog and show it.
        self.dialog.load_settings(cfg_info)
        self.dialog.show()

    @on("new_file_dialog")
    def file_dialog(self, d_type:str, title_msg:str, filter_msg:str) -> None:
        """ Present a dialog for the user to select dictionary files. Attempt to load them if not empty. """
        (filenames, _) = QFileDialog.getOpenFileNames(self.window, title_msg, ".", filter_msg)
        if filenames:
            self.engine_call("new_status", f"Loading {d_type}...")
            self.engine_call(d_type + "_load", filenames)
            self.engine_call("new_status", f"Loaded {d_type} from file dialog.")
