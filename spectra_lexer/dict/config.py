import ast

# File name for the standard user config file (in app data directory).
_CONFIG_FILE_NAME = "~/config.cfg"


class ConfigManager:
    """ Configuration parser for the Spectra program. Config file may be specified with command-line arguments. """

    cfg_file: str    # Path to config file; default is in the user's app data directory.
    _cfg_data: dict  # Dict with config data values loaded from disk.

    def __init__(self, cfg:str=None):
        self.cfg_file = cfg or _CONFIG_FILE_NAME
        self._cfg_data = {}

    def from_raw(self, d:dict=None) -> dict:
        """ Try to convert Python literal strings to objects. This fixes crap like bool('False') = True. """
        if d is None:
            return {}
        for (sect, page) in d.items():
            for (opt, val) in page.items():
                if isinstance(val, str):
                    try:
                        d[sect][opt] = ast.literal_eval(val)
                    except (SyntaxError, ValueError):
                        continue
        self._cfg_data = d
        return d

    def to_raw(self, new_data:dict) -> dict:
        """ Update config options (unless it's the data we just loaded above) and return everything."""
        if new_data is not self._cfg_data:
            for (s, d) in new_data.items():
                self._cfg_data[s].update(d)
        return self._cfg_data
