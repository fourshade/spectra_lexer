"""" Module specifically for managing configurable components, including loading and saving contents to/from disk. """

from spectra_lexer import Component, on, pipe

# File name for the standard user config file (in app data directory).
_CONFIG_FILE_NAME = "~/config.cfg"


class ConfigManager(Component):
    """ Configuration manager for the Spectra program. Config file may be specified with command-line arguments.
        This component handles values from the file only, not specifics such as defaults and types. """

    _cfg_path: str = _CONFIG_FILE_NAME  # Path to config file; default is in the user's app data directory.

    @pipe("start", "new_config_data")
    def start(self, cfg:str=None, **opts) -> dict:
        """ Load all config options from the given path (if any) and send them to components. """
        if cfg is not None:
            self._cfg_path = cfg
        try:
            return self.engine_call("file_load", self._cfg_path)
        except OSError:
            return {}

    @on("config_save")
    def save(self, cfg_data:dict) -> None:
        """ Save a full config data dict to the stored path. Saving should not fail silently, unlike loading. """
        self.engine_call("file_save", self._cfg_path, cfg_data)
