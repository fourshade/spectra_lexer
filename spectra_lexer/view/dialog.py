from .base import VIEW
from spectra_lexer.resource import ConfigDictionary, StenoIndex


class ViewDialog(VIEW):
    """ Handles GUI-centric config and dialog-based operations. """

    def Load(self) -> None:
        self.VIEWConfigUpdate(self.CONFIG)
        if not self.INDEX:
            self.VIEWDialogNoIndex()

    def VIEWConfigUpdate(self, cfg:ConfigDictionary) -> None:
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
