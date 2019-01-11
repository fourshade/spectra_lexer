from functools import partial

from PyQt5.QtWidgets import QMainWindow

from spectra_lexer import Component, on, pipe
from spectra_lexer.gui_qt.config.config_dialog import ConfigDialog


class GUIQtConfig(Component):
    """ GUI configuration manager dialog; allows editing of config values for any component. """

    ROLE = "gui_config"

    window: QMainWindow          # Main window object. Must be the parent of any new dialogs.
    dialog: ConfigDialog = None  # Main dialog object. Should persist when closed/hidden.

    _cfg_info: dict              # Dict with detailed config info from active components.

    def __init__(self, window:QMainWindow):
        super().__init__()
        self.window = window
        self._cfg_info = {}

    @on("start")
    def start(self, **opts) -> None:
        """ If the menu is used, add the config dialog command. """
        self.engine_call("gui_menu_add", "Tools", "Edit Configuration...", "sig_config_dialog_open")

    @on("new_config_info")
    def new_data(self, role:str, cfg_info:dict):
        """ Store a single component's full set of config info by role. """
        self._cfg_info[role] = cfg_info

    @on("sig_config_dialog_open")
    def open(self) -> None:
        """ Create the dialog on first open and connect all Qt signals. """
        if self.dialog is None:
            self.dialog = ConfigDialog(self.window)
            self.dialog.accepted.connect(partial(self.engine_call, "sig_config_dialog_save"))
        # Load all supported config info for the current components into the dialog and show it.
        self.dialog.load_settings(self._cfg_info)
        self.dialog.show()

    @pipe("sig_config_dialog_save", "new_config")
    def save(self) -> dict:
        """ Gather the changed settings from the dialog, send them to the components, and save them to disk. """
        d = self.dialog.save_settings()
        self.engine_call("dict_save_config", None, d)
        return d
