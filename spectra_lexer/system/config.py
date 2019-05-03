from typing import Dict, Optional

from spectra_lexer.core import Component
from spectra_lexer.file import CFG


class ConfigManager(Component):
    """ Configuration parser for the Spectra program. """

    file = resource("cmdline:config-file", "~/config.cfg", desc="CFG file with config settings to load at startup.")

    @init("config")
    def start(self, *dummy) -> None:
        self.load()

    @on("config_load")
    def load(self, filename:str="") -> Dict[str, dict]:
        """ Load all config options from disk. Ignore missing files. """
        d = CFG.load(filename or self.file, ignore_missing=True)
        if d:
            self._update(d)
        return d

    @on("config_save")
    def save(self, d:Dict[str, dict], filename:str="") -> None:
        """ Saving should not fail silently, unlike loading. If no save filename is given, use the default.
            Any component wanting to save the config values probably wants to update them as well. """
        CFG.save(filename or self.file, d)
        self._update(d)

    def _update(self, d:Dict[str, dict]) -> None:
        """ Update all config values on components with a deep broadcast command. """
        self.engine_call("res:config", d, broadcast_depth=2)
