from collections import defaultdict
from typing import Dict, Optional

from spectra_lexer import Component
from spectra_lexer.file import CFG


class ConfigManager(Component):
    """ Configuration parser for the Spectra program. """

    file = resource("cmdline:config-file", "~/config.cfg", desc="CFG file with config settings to load at startup.")

    _info: Dict[str, dict] = {}  # Dict with detailed config info from active components, including the values.

    @on("init:config", pipe_to="res:config::")
    def start(self, config:dict) -> Optional[Dict[str, dict]]:
        """ Send all info and store default data values for active config settings. """
        info = self._info = defaultdict(dict)
        for key, opt in config.items():
            sect, name = key.split(":", 1)
            v = opt.value
            tp = type(v)
            label = name.replace("_", " ").title()
            desc = opt.desc
            if "name" in info[sect]:
                v = info[sect][name][0]
            info[sect][name] = [v, tp, label, desc]
        return self.load()

    @on("config_load", pipe_to="res:config::")
    def load(self, filename:str="") -> Optional[Dict[str, dict]]:
        """ Load all config options from disk. Ignore missing files and convert strings using AST. """
        return self.update(CFG.load(filename or self.file, ignore_missing=True))

    @on("config_save")
    def save(self, d:Dict[str, dict], filename:str="") -> None:
        """ Saving should not fail silently, unlike loading. If no save filename is given, use the default. """
        CFG.save(filename or self.file, d)

    @on("config_update", pipe_to="res:config::")
    def update(self, d:Dict[str, dict]) -> Optional[Dict[str, dict]]:
        """ Update the data dict and all active components with values from the new dict. """
        info = self._info
        for sect, page in d.items():
            p = info[sect]
            for name, val in page.items():
                p[name] = [val, *p[name][1:]]
        self.engine_call("res:cfginfo", info)
        return d
