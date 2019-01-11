import ast
from typing import Iterable, List, Tuple

from spectra_lexer.dict.manager import ResourceManager

# File name for the standard user config file (in app data directory).
_CONFIG_FILE_NAME: str = "~/config.cfg"


class ConfigManager(ResourceManager):
    """ Configuration parser for the Spectra program. Config file may be specified with command-line arguments. """

    ROLE = "dict_config"
    CMD_SUFFIX = "config"
    OPT_KEY = "cfg"

    _cfg_data: dict  # Dict with config data values loaded from disk.

    def load(self, filenames:Iterable[str]=None) -> dict:
        """ Load and merge all config options from disk. Ignore failures and convert strings using AST. """
        try:
            d = super().load(filenames)
        except OSError:
            d = {}
        self._cfg_data = d
        return d

    def load_default(self) -> List[dict]:
        return super()._load([_CONFIG_FILE_NAME])

    def parse(self, d):
        """ Try to convert Python literal strings to objects. This fixes crap like bool('False') = True. """
        for (sect, page) in d.items():
            for (opt, val) in page.items():
                if isinstance(val, str):
                    try:
                        d[sect][opt] = ast.literal_eval(val)
                    except (SyntaxError, ValueError):
                        continue
        return d

    def save(self, filename:str, new_data:dict) -> Tuple[str, dict]:
        """ Update config options to disk and save them to disk. Saving should not fail silently, unlike loading. """
        if filename is None:
            filename = _CONFIG_FILE_NAME
        for (s, d) in new_data.items():
            self._cfg_data[s].update(d)
        return filename, self._cfg_data
