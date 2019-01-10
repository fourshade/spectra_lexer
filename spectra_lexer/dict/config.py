import ast
from typing import Iterable, Tuple

from spectra_lexer import Component, fork, pipe, on
from spectra_lexer.utils import merge

# File name for the standard user config file (in app data directory).
_CONFIG_FILE_NAME = "~/config.cfg"


class ConfigManager(Component):
    """ Configuration parser for the Spectra program. Config file may be specified with command-line arguments. """

    cfg_file: str    # Path to config file; default is in the user's app data directory.
    _cfg_data: dict  # Dict with config data values loaded from disk.

    @on("start")
    def start(self, cfg:str=None, **opts):
        self.cfg_file = cfg or _CONFIG_FILE_NAME
        self._cfg_data = {}

    @fork("dict_load_config", "new_config_data")
    def load_config(self, filenames:Iterable[str]=None) -> dict:
        """ Load and merge all config options from disk. Ignore failures and convert strings using AST. """
        if filenames is None:
            filenames = [self.cfg_file]
        try:
            d = merge([self.engine_call("file_load", f) for f in filenames])
        except OSError:
            d = {}
        self._ast_convert(d)
        return self._cfg_data

    def _ast_convert(self, d) -> None:
        """ Try to convert Python literal strings to objects. This fixes crap like bool('False') = True. """
        self._cfg_data = d
        for (sect, page) in d.items():
            for (opt, val) in page.items():
                if isinstance(val, str):
                    try:
                        d[sect][opt] = ast.literal_eval(val)
                    except (SyntaxError, ValueError):
                        continue

    @pipe("dict_save_config", "file_save", unpack=True)
    def save_config(self, new_data:dict, filename:str=None) -> Tuple[str, dict]:
        """ Update config options to disk and save them to disk. Saving should not fail silently, unlike loading. """
        if filename is None:
            filename = self.cfg_file
        for (s, d) in new_data.items():
            self._cfg_data[s].update(d)
        return filename, self._cfg_data
