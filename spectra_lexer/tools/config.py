from collections import defaultdict
from typing import Dict

from spectra_lexer import Component


class ConfigDialogTool(Component):
    """ Config dialog manager; allows editing of config values for any component. """

    config_menu = Option("menu", "Tools:Edit Configuration...", ["config_dialog_open"])

    _data: Dict[str, dict]  # Dict with config values from all components loaded from disk.
    _info: Dict[str, dict]  # Dict with detailed config info from active components (but not the values).

    @on("setup")
    def new_options(self, *, config=(), **options) -> None:
        """ Store all info and default data values for active config settings. """
        info = self._info = defaultdict(dict)
        data = self._data = defaultdict(dict)
        for opt in config:
            sect, name = opt.key.split(":", 1)
            tp = type(opt.default)
            label = name.replace("_", " ").title()
            desc = opt.desc
            info[sect][name] = (tp, label, desc)
            data[sect][name] = opt.default

    @pipe("config_dialog_open", "new_dialog")
    def open_dialog(self) -> tuple:
        """ Create GUI configuration manager dialog by combining info and data dict values. """
        data = self._data
        d = {sect: {name: (data[sect][name], *opt)
                    for name, opt in page.items()}
             for sect, page in self._info.items()}
        return "config", d

    @pipe("config_dialog_result", "config_save")
    def save(self, d:Dict[str, dict]) -> Dict[str, dict]:
        """ Update components with the new config values and save them. """
        self.update_values(d)
        return self._data

    @on("new_config")
    def update_values(self, d:Dict[str, dict]) -> None:
        """ Update our data dict with new config values from the given dict. """
        for sect, page in d.items():
            self._data[sect].update(page)
