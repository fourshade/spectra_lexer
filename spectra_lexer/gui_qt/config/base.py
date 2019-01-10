from functools import partial

from PyQt5.QtWidgets import QMainWindow

from spectra_lexer import Component, on, pipe
from spectra_lexer.gui_qt.config.config_dialog import ConfigDialog


class GUIQtConfig(Component):
    """ GUI configuration manager dialog; allows editing of config values for any component. """

    window: QMainWindow          # Main window object. Must be the parent of any new dialogs.
    dialog: ConfigDialog = None  # Main dialog object. Should persist when closed/hidden.
    _cfg_data: dict = {}         # Dict with config data values loaded from disk.
    _cfg_info: dict = {}         # Dict with detailed config info from active components.

    def __init__(self, window:QMainWindow):
        super().__init__()
        self.window = window

    @on("start")
    def start(self, **opts) -> None:
        """ If the menu is used, add the config dialog command. """
        self.engine_call("gui_menu_add", "Tools", "Edit Configuration...", "sig_config_dialog_open")

    @on("new_config_data")
    def configure(self, cfg_data:dict) -> None:
        """ Store all data values from disk, if only so that inactive component options won't be lost upon write.
            This component has no config options itself, so it is safe to override the configure command. """
        self._cfg_data = cfg_data

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

    @pipe("sig_config_dialog_save", "new_config_data")
    def save(self) -> dict:
        """ Overwrite settings in the current config data from those in the dialog.
            Send the changed settings to the components and also save them to disk. """
        new_data = self.dialog.save_settings()
        for (s, d) in new_data.items():
            self._cfg_data[s].update(d)
        self.engine_call("config_save", self._cfg_data)
        return self._cfg_data
