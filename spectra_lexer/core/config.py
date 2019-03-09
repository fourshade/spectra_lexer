from typing import Dict, Optional

from spectra_lexer import Component
from spectra_lexer.utils import str_eval


class ConfigManager(Component):
    """ Configuration parser for the Spectra program. """

    file = Option("cmdline", "config-file", "~/config.cfg", "CFG or INI file with config settings to load at startup.")

    @pipe("start", "new_config")
    @pipe("config_load", "new_config")
    def load(self, filename:str="") -> Optional[Dict[str, dict]]:
        """ Load all config options from disk. Ignore failures and convert strings using AST. """
        try:
            d = self.engine_call("file_load", filename or self.file)
        except OSError:
            return None
        # Try to convert Python literal strings to objects. This fixes crap like bool('False') = True.
        for page in d.values():
            for (opt, val) in page.items():
                if isinstance(val, str):
                    page[opt] = str_eval(val)
        self._update_components(d)
        return d

    @pipe("config_save", "file_save")
    def save(self, d:Dict[str, dict], filename:str="") -> tuple:
        """ Send a new set of config values to the components and save them to disk.
            Saving should not fail silently, unlike loading. If no save filename is given, use the default file. """
        self._update_components(d)
        return (filename or self.file), d

    def _update_components(self, d:Dict[str, dict]) -> None:
        """ Update all active components with values from the given dict. """
        for sect, page in d.items():
            for name, val in page.items():
                self.engine_call(f"set_config_{sect}:{name}", val)
