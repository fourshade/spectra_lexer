from collections import defaultdict
from functools import partial
from typing import Dict

from spectra_lexer import Component


class ConfigDialogTool(Component):
    """ Config dialog manager. """

    config_menu = Option("menu", "Tools:Edit Configuration...", ["config_dialog"])

    _cfg_data: Dict[str, dict]   # Dict with config values from all components loaded from disk.
    _cfg_info: Dict[str, dict]   # Dict with detailed config info from active components.

    @on("setup")
    def new_options(self, *, config=(), **options) -> None:
        """ Store all info and default data values for active config settings. """
        info = self._cfg_info = defaultdict(dict)
        self._cfg_data = defaultdict(dict)
        for opt in config:
            sect, name = opt.key.split(":", 1)
            info[sect][name] = opt

    @on("new_config")
    def update_values(self, d:Dict[str, dict]) -> None:
        """ Update our data dict and all active components with values from the given dict. """
        for sect, page in d.items():
            self._cfg_data[sect].update(page)

    @on("config_dialog")
    def new_dialog(self) -> None:
        """ Create GUI configuration manager dialog; allows editing of config values for any component. """
        cb = partial(self.engine_call, "config_accept")
        dialog = self.engine_call("gui_window_config_dialog", cb, self._cfg_info)
        # Load all supported config info for the current components into the dialog and show it.
        dialog.load_settings(self._cfg_data)
        dialog.show()

    @pipe("config_accept", "config_save")
    def save(self, d:Dict[str, dict]) -> Dict[str, dict]:
        """ Update our data dict and all active components with values from the given dict and save it. """
        self.update_values(d)
        return self._cfg_data
