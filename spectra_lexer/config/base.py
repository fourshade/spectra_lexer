"""" Module specifically for managing configurable components, including loading and saving contents to/from disk. """

from spectra_lexer import Component, on

# File name for the standard user config file (in app data directory).
_CONFIG_FILE_NAME = "~/config.cfg"


class ConfigManager(Component):
    """ Configuration manager for the Spectra program. Config file may be specified with command-line arguments.
        Setup must occur before anything configurable is allowed to run. """

    _cfg_path: str = _CONFIG_FILE_NAME  # Path to config file; default is in the user's app data directory.
    _cfg_dict: dict = None              # Master dict; holds all config values for all components.

    @on("start")
    def start(self, cfg:str=None, **opts) -> None:
        """ Load all config options from the given path (if any) and send them to components. """
        if cfg is not None:
            self._cfg_path = cfg
        self.load()

    @on("config_load")
    def load(self) -> None:
        """ Load the master config dict (if it exists) and send it to the components. """
        try:
            self._cfg_dict = self.engine_call("file_load", self._cfg_path)
        except OSError:
            self._cfg_dict = {}
        self.engine_call("configure", self._cfg_dict)

    @on("config_save")
    def save(self) -> None:
        """ Save the master config dict. Saving should not fail silently, unlike loading. """
        self.engine_call("file_save", self._cfg_path, self._cfg_dict)
