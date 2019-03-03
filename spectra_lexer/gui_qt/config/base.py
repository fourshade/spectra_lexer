from functools import partial
from typing import Dict

from PyQt5.QtWidgets import QMainWindow, QWidget

from spectra_lexer import Component, on
from spectra_lexer.gui_qt.config.config_dialog import ConfigDialog


class GUIQtConfigDialog(Component):
    """ GUI configuration manager dialog; allows editing of config values for any component. """

    ROLE = "gui_config"

    window: QMainWindow          # Main window object. Must be the parent of any new dialogs.
    dialog: ConfigDialog = None  # Main dialog object. Should persist when closed/hidden.

    @on("new_gui_window")
    def start(self, widgets:Dict[str, QWidget]) -> None:
        """ Get the required widgets and add the config dialog command. """
        self.window = widgets["window"][0]
        self.engine_call("gui_menu_add", "Tools", "Edit Configuration...", "config_dialog")

    @on("new_config_dialog")
    def new_dialog(self, cfg_info:dict) -> None:
        """ Create the dialog with the engine callback on first open. """
        if self.dialog is None:
            self.dialog = ConfigDialog(self.window, partial(self.engine_call, "config_save"))
        # Load all supported config info for the current components into the dialog and show it.
        self.dialog.load_settings(cfg_info)
        self.dialog.show()
