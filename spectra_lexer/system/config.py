from collections import defaultdict
from typing import Dict

from .cmdline import CmdlineOption
from .console import ConsoleCommand
from spectra_lexer.core import COREApp, Component, Option, Resource
from spectra_lexer.system.file import SYSFile
from spectra_lexer.types.codec import CFGDict


class ConfigDictionary(CFGDict):
    pass


class ConfigOption(Option):
    pass


class SYSConfig:

    @ConsoleCommand("config_load")
    def load(self, filename:str) -> ConfigDictionary:
        """ Load all config options from disk. Ignore missing files. """
        raise NotImplementedError

    @ConsoleCommand("config_save")
    def save(self, d:Dict[str, dict], filename:str) -> None:
        """ Saving should not fail silently, unlike loading. If no save filename is given, use the default.
            Any component wanting to save the config values probably wants to update them as well. """
        raise NotImplementedError

    class Info:
        info: ConfigDictionary = Resource()


class ConfigManager(Component, SYSConfig,
                    COREApp.Start):
    """ Configuration parser for the Spectra program. """

    file = CmdlineOption("config-file", default="~/config.cfg",
                         desc="CFG file with config settings to load at startup.")
    res_info: dict = ConfigOption.init_info()

    _all_info: dict = {}  # Dict with detailed config info from active components, including the values.

    def on_app_start(self) -> None:
        """ Make a dict with detailed config info from active components. """
        self._all_info = info = defaultdict(dict)
        for sect, page in self.res_info.items():
            d = info[sect]
            for key, opt in page.items():
                default, desc = opt.info
                v = default
                tp = type(v)
                label = key.replace("_", " ").title()
                if "name" in d:
                    v = d[key][0]
                d[key] = [v, tp, label, desc]
        self.load()

    def load(self, filename:str="") -> ConfigDictionary:
        """ Load all config options from disk. Ignore missing files. """
        data = self.engine_call(SYSFile.read, filename or self.file, ignore_missing=True)
        d = ConfigDictionary.decode(data)
        self._update(d)
        return d

    def save(self, d:Dict[str, dict], filename:str="") -> None:
        """ Saving should not fail silently, unlike loading. If no save filename is given, use the default.
            Any component wanting to save the config values probably wants to update them as well. """
        cfg = ConfigDictionary(d)
        self.engine_call(SYSFile.write, filename or self.file, cfg.encode())
        self._update(cfg)

    def _update(self, d:ConfigDictionary) -> None:
        """ Update all config values on existing components with a deep nested command set. """
        info = self._all_info
        for sect, page in d.items():
            p = info[sect]
            for name, val in page.items():
                if name in p:
                    old_val, *rest = p[name]
                    p[name] = [val, *rest]
        self.engine_call(self.Info, info)
        for sect, page in info.items():
            for name, (val, *_) in page.items():
                self.engine_call(ConfigOption.response(sect, name), val)
