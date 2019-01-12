from typing import Sequence

from spectra_lexer.dict.manager import ResourceManager

# File name for the standard user config file (in app data directory).
from spectra_lexer.utils import str_eval

_CONFIG_FILE_NAME: str = "~/config.cfg"


class ConfigManager(ResourceManager):
    """ Configuration parser for the Spectra program. Config file may be specified with command-line arguments. """

    ROLE = "dict_config"
    files = [_CONFIG_FILE_NAME]

    _cfg_data: dict  # Dict with config data values loaded from disk.

    def load(self, filenames:Sequence[str]=()) -> dict:
        """ Load and merge all config options from disk. Ignore failures and convert strings using AST. """
        try:
            d = super().load(filenames)
        except OSError:
            d = {}
        self._cfg_data = d
        return d

    def parse(self, d:dict) -> dict:
        """ Try to convert Python literal strings to objects. This fixes crap like bool('False') = True. """
        for (sect, page) in d.items():
            for (opt, val) in page.items():
                if isinstance(val, str):
                    d[sect][opt] = str_eval(val)
        return d

    def inv_parse(self, new_data:dict) -> dict:
        """ Update config options to prepare to save to disk. Saving should not fail silently, unlike loading. """
        for (s, d) in new_data.items():
            self._cfg_data[s].update(d)
        return self._cfg_data
