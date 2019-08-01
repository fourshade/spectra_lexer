from typing import Dict, List

from .base import VIEW
from .config import ConfigDictionary
from .state import ViewState
from spectra_lexer.core import CORE
from spectra_lexer.resource import RS
from spectra_lexer.steno import LX


class ViewManager(CORE, RS, LX, VIEW):
    """ Handles GUI interface-based operations. """

    _config: ConfigDictionary  # Keeps track of configuration options in a master dict.

    def __init__(self) -> None:
        self._config = ConfigDictionary(ViewState.CONFIG_INFO)

    def RSConfigReady(self, cfg:Dict[str, dict]) -> None:
        self._config.sectioned_update(cfg)
        self._update_info()

    def VIEWConfigUpdate(self, options:dict) -> None:
        self._config.update(options)
        out = self._config.sectioned_data()
        self.RSConfigSave(out)
        self._update_info()

    def _update_info(self) -> None:
        self.VIEWConfigInfo(self._config.info())

    def VIEWDialogMakeIndex(self, index_size:int) -> None:
        self._msg("Making new index...")
        index = self.LXAnalyzerMakeIndex(index_size)
        self.RSIndexSave(index)
        self.RSIndexReady(index)
        self._msg("Successfully created index!" if index_size else "Skipped index creation.")
        self.VIEWDialogIndexDone()

    def VIEWDialogFileLoad(self, filenames:List[str], res_type:str) -> None:
        getattr(self, f"RS{res_type.title()}Load")(*filenames)
        self._msg(f"Loaded {res_type} from file dialog.")

    def _msg(self, msg:str) -> None:
        """ Send a message that we've started or finished with an operation. """
        self.COREStatus(msg)

    def VIEWAction(self, state:dict, action:str="") -> None:
        """ Add config options to the state before processing (but only those the state doesn't already define). """
        result = ViewState(state, self, **self._config).run(action)
        if result is not None:
            self.VIEWActionResult(result)
