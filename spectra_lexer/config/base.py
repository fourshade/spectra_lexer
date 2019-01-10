"""" Module specifically for managing configurable components, including loading and saving contents to/from disk. """

import ast

from spectra_lexer import Component, pipe

# File name for the standard user config file (in app data directory).
_CONFIG_FILE_NAME = "~/config.cfg"


class ConfigManager(Component):
    """ Configuration manager for the Spectra program. Config file may be specified with command-line arguments.
        This component handles values from the file only, not specifics such as defaults and types. """

    _cfg_path: str   # Path to config file; default is in the user's app data directory.
    _cfg_data: dict  # Dict with config data values loaded from disk.

    @pipe("start", "new_config_data")
    def start(self, cfg:str=_CONFIG_FILE_NAME, **opts) -> dict:
        """ Load all config options from the given path (or default if None) and send them to components. """
        self._cfg_path = cfg
        self.load()
        return self._cfg_data

    def load(self) -> None:
        """ Load config options from disk. Use an empty dict (for defaults) if nothing was found. """
        try:
            self._cfg_data = self.engine_call("file_load", self._cfg_path)
            _ast_convert(self._cfg_data)
        except OSError:
            self._cfg_data = {}

    @pipe("new_config_data", "file_save", unpack=True)
    def update(self, new_data:dict) -> tuple:
        """ Update config options and save to disk (unless it's the data we just loaded above).
            Saving should not fail silently, unlike loading. """
        if new_data is not self._cfg_data:
            for (s, d) in new_data.items():
                self._cfg_data[s].update(d)
            return self._cfg_path, self._cfg_data


def _ast_convert(d:dict) -> None:
    """ Try to convert Python literal strings in a dict to objects. This fixes crap like bool('False') = True. """
    for (sect, page) in d.items():
        for (opt, val) in page.items():
            if isinstance(val, str):
                try:
                    d[sect][opt] = ast.literal_eval(val)
                except (SyntaxError, ValueError):
                    continue
