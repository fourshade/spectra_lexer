from collections import defaultdict
from typing import Dict

from .config_dialog import ConfigDialog
from spectra_lexer import Component


class ConfigDialogTool(Component):
    """ Config dialog manager; allows editing of config values for any component. """

    config_menu = Resource("menu", "Tools:Edit Configuration...", ["config_dialog_open"])
    window = Resource("gui", "window", None, "Main window object. Must be the parent of any new dialogs.")

    _data: Dict[str, dict]  # Dict with config values from all components loaded from disk.
    _info: Dict[str, dict]  # Dict with detailed config info from active components (but not the values).

    def __init__(self):
        super().__init__()
        self._info = defaultdict(dict)
        self._data = defaultdict(dict)

    @on("start")
    def start(self, *, config=(), **options) -> None:
        """ Store all info and default data values for active config settings. """
        info = self._info
        data = self._data
        for opt in config:
            sect, name = opt.key.split(":", 1)
            tp = type(opt.default)
            label = name.replace("_", " ").title()
            desc = opt.desc
            info[sect][name] = (tp, label, desc)
            data[sect].setdefault(name, opt.default)

    @on("set_dict_config")
    def update_values(self, d:Dict[str, dict]) -> None:
        """ Update our data dict with new config values from the given dict. """
        for sect, page in d.items():
            self._data[sect].update(page)

    @on("config_dialog_open")
    def open_dialog(self) -> None:
        """ Create and show GUI configuration manager dialog by combining info and data dict values. """
        data = self._data
        d = {sect: {name: (data[sect][name], *opt)
                    for name, opt in page.items()}
             for sect, page in self._info.items()}
        ConfigDialog(self.window, self.save, d).show()

    def save(self, d:Dict[str, dict]) -> None:
        """ Update components with the new config values and save them. """
        self.update_values(d)
        self.engine_call("config_save", self._data)
