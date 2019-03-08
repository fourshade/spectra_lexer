from collections import defaultdict
from typing import Dict

from spectra_lexer import Component
from spectra_lexer.utils import str_eval


class ConfigManager(Component):
    """ Configuration parser for the Spectra program. """

    file = Option("cmdline", "config-file", "~/config.cfg", "Config .cfg or .ini file to load at startup.")

    _cfg_data: Dict[str, dict]  # Dict with config values from all components loaded from disk.
    _cfg_info: Dict[str, dict]  # Dict with detailed config info from active components.

    @on("config_options")
    def new_options(self, options:list) -> None:
        """ Store all active config option info by owner section and option name. Data values start at default. """
        info = self._cfg_info = defaultdict(dict)
        data = self._cfg_data = defaultdict(dict)
        for opt in options:
            sect, name = opt.key.split(":", 1)
            info[sect][name] = opt
            data[sect][name] = opt.default

    @pipe("start", "config_load")
    def start(self, **opts) -> tuple:
        """ Add the config dialog command and load the config file. """
        self.engine_call("new_menu_item", "Tools", "Edit Configuration...", "config_dialog")
        return ()

    @on("config_load")
    def load(self, filename:str="") -> None:
        """ Update all config options from disk. Ignore failures and convert strings using AST. """
        try:
            d = self.engine_call("file_load", filename or self.file)
        except OSError:
            return
        # Try to convert Python literal strings to objects. This fixes crap like bool('False') = True.
        for page in d.values():
            for (opt, val) in page.items():
                if isinstance(val, str):
                    page[opt] = str_eval(val)
        self._update_values(d)

    @pipe("config_dialog", "new_config_dialog")
    def dialog(self) -> tuple:
        """ Open a dialog for configuration using the current settings info and values. """
        return self._cfg_info, self._cfg_data

    @pipe("config_save", "file_save")
    def save(self, d:Dict[str, dict], filename:str="") -> tuple:
        """ Update the current config values, send them to the components, and save *everything* to disk.
            Saving should not fail silently, unlike loading. If no save filename is given, use the default file. """
        self._update_values(d)
        return (filename or self.file), self._cfg_data

    def _update_values(self, d:Dict[str, dict]) -> None:
        """ Update our data dict and all active components with values from the given dict. """
        for sect, page in d.items():
            self._cfg_data[sect].update(page)
            for name, val in page.items():
                self.engine_call(f"set_config_{sect}:{name}", val)
