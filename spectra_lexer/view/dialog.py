from .base import ConfigDictionary, VIEW
from spectra_lexer.resource import StenoIndex
from spectra_lexer.system import CmdlineOption


class ViewDialog(VIEW):
    """ Handles GUI-centric config and dialog-based operations. """

    config_file: str = CmdlineOption("config-file", default="~/config.cfg",
                                     desc="CFG file with config settings to load at start and/or write to.")

    def Load(self) -> None:
        self.VIEWConfigLoad(self.config_file)
        if not self.INDEX:
            self.VIEWDialogNoIndex()

    def VIEWConfigLoad(self, *patterns:str, **kwargs) -> ConfigDictionary:
        data_list = self.SYSFileLoad(*patterns)
        cfg = ConfigDictionary.decode(*data_list, **kwargs)
        self._update_config(cfg)
        return cfg

    def VIEWConfigSave(self, cfg:ConfigDictionary, filename:str="", **kwargs) -> None:
        data = cfg.encode(**kwargs)
        self.SYSFileSave(data, filename or self.config_file)
        self._update_config(cfg)

    def _update_config(self, cfg:ConfigDictionary) -> None:
        """ Update the config resource and all config values on existing components. """
        self.CONFIG = cfg
        self.CONFIG_INFO = [(sect, name, val) for sect, page in cfg.items() for name, val in page.items()]

    def VIEWDialogMakeIndex(self, index_size:int) -> None:
        """ A sentinel value is required in empty indices to distinguish them from defaults. """
        if index_size:
            self._msg("Making new index...")
            index = self.LXLexerMakeIndex(index_size)
            self._msg("Successfully created index!")
        else:
            index = StenoIndex()
            self._msg("Skipped index creation.")
        if not index:
            index["SENTINEL"] = {}
        self.RSIndexSave(index)
        self.INDEX = index

    def VIEWDialogFileLoad(self, filenames:list, res_type:str) -> None:
        getattr(self, f"RS{res_type.title()}Load")(*filenames)
        self._msg(f"Loaded {res_type} from file dialog.")

    def _msg(self, msg:str) -> None:
        """ Send a message that we've started or finished with an operation. """
        self.SYSStatus(msg)
