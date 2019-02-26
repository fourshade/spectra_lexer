from typing import Sequence

from spectra_lexer import Component, pipe
from spectra_lexer.utils import str_eval

# File name for the standard user config file (in app data directory).
_CONFIG_FILE_NAME = "~/config.cfg"


class ConfigManager(Component):
    """ Configuration parser for the Spectra program. Config file may be specified with command-line arguments. """

    ROLE = "config"

    _cfg_data: dict  # Dict with config data values loaded from disk.

    @pipe("start", "config_load")
    def start(self, config:str=None, **opts) -> Sequence[str]:
        """ If there is a command line option for this component, even if empty, attempt to load config.
            If the option is present but empty (or otherwise evaluates False), use the default instead. """
        if config is not None:
            return config or ()

    @pipe("config_load", "new_config")
    def load(self, filename:str=_CONFIG_FILE_NAME) -> dict:
        """ Load all config options from disk. Ignore failures and convert strings using AST. """
        try:
            d = self.engine_call("file_load", filename)
        except OSError:
            return {}
        # Try to convert Python literal strings to objects. This fixes crap like bool('False') = True.
        for page in d.values():
            for (opt, val) in page.items():
                if isinstance(val, str):
                    page[opt] = str_eval(val)
        self._cfg_data = d
        return d

    @pipe("config_save", "file_save")
    def save(self, new_data:dict, filename:str="") -> tuple:
        """ Update config options and save them to disk. Saving should not fail silently, unlike loading.
            If no save filename is given, use the default file. """
        for (s, d) in new_data.items():
            self._cfg_data.setdefault(s, {}).update(d)
        return (filename or _CONFIG_FILE_NAME), self._cfg_data
