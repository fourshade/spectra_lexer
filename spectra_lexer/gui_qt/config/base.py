from collections import defaultdict
from functools import partial

from PyQt5.QtWidgets import QMainWindow

from spectra_lexer import Component, on, pipe
from spectra_lexer.options import CFGOption
from spectra_lexer.gui_qt.config.config_dialog import ConfigDialog


class GUIQtConfig(Component):
    """ GUI configuration manager dialog; allows editing of config values for any component. """

    ROLE = "gui_config"

    window: QMainWindow          # Main window object. Must be the parent of any new dialogs.
    dialog: ConfigDialog = None  # Main dialog object. Should persist when closed/hidden.

    _cfg_info: defaultdict       # Dict with detailed config info from active components.

    def __init__(self, window:QMainWindow):
        super().__init__()
        self.window = window
        self._cfg_info = defaultdict(dict)

    @on("start")
    def start(self, show_menu=True, **opts) -> None:
        """ If the menu is used, add the config dialog command. """
        if show_menu:
            self.engine_call("gui_menu_add", "Tools", "Edit Configuration...", "gui_config_open")

    @on("new_config_info")
    def set_config_info(self, role:str, key:str, option:CFGOption):
        """ Store a single config option by owner role and option key. """
        self._cfg_info[role][key] = option

    @on("gui_config_open")
    def open(self) -> None:
        """ Create the dialog on first open and connect all Qt signals. """
        if self.dialog is None:
            self.dialog = ConfigDialog(self.window)
            self.dialog.accepted.connect(partial(self.engine_call, "gui_config_save"))
        # Load all supported config info for the current components into the dialog and show it.
        self.dialog.load_settings(self._cfg_info)
        self.dialog.show()

    @pipe("gui_config_save", "new_config")
    def save(self) -> dict:
        """ Gather the changed settings from the dialog, send them to the components, and save them to disk. """
        d = self.dialog.save_settings()
        self.engine_call("config_save", d)
        return d
