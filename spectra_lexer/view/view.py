from .base import VIEW
from .config import ConfigDictionary
from .state import ViewState
from spectra_lexer.resource import StenoIndex
from spectra_lexer.system import CmdlineOption


class ViewManager(VIEW):
    """ Handles GUI interface-based operations. """

    config_file: str = CmdlineOption("config-file", default="~/config.cfg",
                                     desc="CFG file with config settings to load at start and/or write to.")

    _config: ConfigDictionary = None  # Keeps track of configuration options in a master dict.

    def Load(self) -> None:
        data_list = self.SYSFileLoad(self.config_file)
        cfg = ConfigDictionary.decode(*data_list)
        self._update_info(cfg)
        if not self.INDEX:
            self.VIEWDialogNoIndex()

    def VIEWConfigUpdate(self, options:dict) -> None:
        cfg = ConfigDictionary(options)
        self.SYSFileSave(cfg.encode(), self.config_file)
        self._update_info(cfg)

    def _update_info(self, cfg:ConfigDictionary):
        self._config = cfg
        self.VIEWConfigInfo(cfg.info())

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
        self.VIEWDialogIndexDone()

    def VIEWDialogFileLoad(self, filenames:list, res_type:str) -> None:
        getattr(self, f"RS{res_type.title()}Load")(*filenames)
        self._msg(f"Loaded {res_type} from file dialog.")

    def _msg(self, msg:str) -> None:
        """ Send a message that we've started or finished with an operation. """
        self.SYSStatus(msg)

    def VIEWAction(self, state:dict, action:str="") -> None:
        self._config.write_to(state)
        result = ViewState(state, self).run(action)
        if result is not None:
            self.VIEWActionResult(result)
