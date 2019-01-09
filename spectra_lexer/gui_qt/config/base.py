from functools import partial

from PyQt5.QtWidgets import QMainWindow

from spectra_lexer import Component, on, pipe
from spectra_lexer.gui_qt.config.config_dialog import ConfigDialog


class GUIQtConfig(Component):
    """ GUI configuration manager dialog; allows editing of config values for any component. """

    window: QMainWindow          # Main window object. Must be the parent of any new dialogs.
    dialog: ConfigDialog = None  # Main dialog object. Should persist when closed/hidden.
    _cfg_dict: dict = {}         # Active reference to the master config dict.

    def __init__(self, window:QMainWindow):
        super().__init__()
        self.window = window

    @on("start")
    def start(self, **opts) -> None:
        """ If the menu is used, add the config dialog command. """
        self.engine_call("gui_menu_add", "Tools", "Edit Configuration...", "sig_config_dialog_open")

    @on("configure")
    def configure(self, cfg_dict:dict) -> None:
        """ Save the reference to the master config dict and use it to dynamically view/alter the config state.
            This component has no config options itself, so it is safe to override the configure command. """
        self._cfg_dict = cfg_dict

    @on("sig_config_dialog_open")
    def open(self) -> None:
        """ Create the dialog on first open and connect all Qt signals. """
        if self.dialog is None:
            self.dialog = ConfigDialog(self.window)
            self.dialog.accepted.connect(partial(self.engine_call, "sig_config_dialog_save"))
        # Load the current settings into the dialog and display it once finished.
        self.dialog.load_settings(self._cfg_dict)
        self.dialog.show()

    @pipe("sig_config_dialog_save", "config_save", unpack=True)
    def save(self) -> tuple:
        """ Replace the master config dict's children in-place with the current settings in the dialog.
            This will immediately affect the program. Save the settings to disk as well. """
        new_cfg = self.dialog.save_settings()
        for k, d in self._cfg_dict.items():
            d.clear()
            d.update(new_cfg[k])
        return ()
