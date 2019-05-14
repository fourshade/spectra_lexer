from .base import ConfigDictionary, VIEW
from spectra_lexer.system import CmdlineOption


class ConfigResourceManager(VIEW):
    """ Configuration parser for the Spectra program. """

    config_file: str = CmdlineOption("config-file", default="~/config.cfg",
                                     desc="CFG file with config settings to load at start and/or write to.")

    def Load(self) -> None:
        self.VIEWConfigLoad(self.config_file)

    def VIEWConfigLoad(self, *patterns:str, **kwargs) -> ConfigDictionary:
        cfg = self.CONFIG = self.SYSFileLoad(ConfigDictionary, *patterns, **kwargs)
        self._update(cfg)
        return cfg

    def VIEWConfigSave(self, cfg:ConfigDictionary, filename:str="", **kwargs) -> None:
        self.SYSFileSave(cfg, filename or self.config_file, **kwargs)
        self._update(cfg)

    def _update(self, cfg:ConfigDictionary) -> None:
        """ Update all config values on existing components by setting descriptors manually. """
        self.CONFIG_INFO = [(sect, name, val) for sect, page in cfg.items() for name, val in page.items()]
