from typing import List

from .base import VIEW
from .config import ConfigDictionary, ConfigInfo
from .state import ViewState
from spectra_lexer.core import CmdlineOption, CORE
from spectra_lexer.resource import RS, RulesDictionary, StenoIndex, TranslationsDictionary
from spectra_lexer.steno import LX
from spectra_lexer.system import SYS


class ViewManager(CORE, SYS, RS, LX, VIEW):
    """ Handles GUI interface-based operations. """

    OPTIONS = ConfigInfo(("compound_board", True, "board", "compound_keys",
                         "Show special labels for compound keys (i.e. `f` instead of TP)."),
                         ("recursive_graph", True, "graph", "recursive",
                         "Include rules that make up other rules."),
                         ("compressed_graph", True, "graph", "compressed",
                         "Compress the graph vertically to save space."),
                         ("match_all_keys", False, "lexer", "need_all_keys",
                         "Only return lexer results that match every key in the stroke."),
                         ("matches_per_page", 100, "search", "match_limit",
                         "Maximum number of matches returned on one page of a search."),
                         ("links_enabled", True, "search", "example_links",
                         "Show hyperlinks to indexed examples of selected rules."))

    config_file: str = CmdlineOption("config-file", default="~/config.cfg",
                                     desc="CFG file with config settings to load at start and/or write to.")

    _rules: RulesDictionary = None
    _translations: TranslationsDictionary = None
    _index: StenoIndex = None
    _config: ConfigDictionary = None  # Keeps track of configuration options in a master dict.

    def Load(self) -> None:
        cfg = self._config = ConfigDictionary(self.OPTIONS)
        data_list = self.SYSFileLoad(self.config_file)
        cfg.decode_update(*data_list)
        self._update_info(cfg)
        if not self._index:
            self.VIEWDialogNoIndex()

    def RSSystemReady(self, rules:RulesDictionary, **kwargs) -> None:
        self._rules = rules

    def RSTranslationsReady(self, translations:TranslationsDictionary) -> None:
        self._translations = translations

    def RSIndexReady(self, index:StenoIndex) -> None:
        self._index = index

    def VIEWConfigUpdate(self, options:dict) -> None:
        cfg = self._config
        self.SYSFileSave(cfg.encode_update(options), self.config_file)
        self._update_info(cfg)

    def _update_info(self, cfg:ConfigDictionary) -> None:
        self.VIEWConfigInfo(cfg.info())

    def VIEWDialogMakeIndex(self, index_size:int) -> None:
        self._msg("Making new index...")
        index = self.LXLexerMakeIndex(index_size)
        self._save_index(index)
        self._msg("Successfully created index!")
        self.VIEWDialogIndexDone()

    def VIEWDialogSkipIndex(self) -> None:
        """ A sentinel value is required in empty indices to distinguish them from defaults. """
        index = StenoIndex(SENTINEL={})
        self._save_index(index)
        self._msg("Skipped index creation.")

    def _save_index(self, index:StenoIndex) -> None:
        self.RSIndexSave(index)
        self._index = index

    def VIEWDialogFileLoad(self, filenames:List[str], res_type:str) -> None:
        getattr(self, f"RS{res_type.title()}Load")(*filenames)
        self._msg(f"Loaded {res_type} from file dialog.")

    def _msg(self, msg:str) -> None:
        """ Send a message that we've started or finished with an operation. """
        self.SYSStatus(msg)

    def VIEWAction(self, state:dict, action:str="") -> None:
        """ Add config options to the state before processing (but only those the state doesn't already define). """
        self._config.write_to(state)
        result = ViewState(state, self).run(action)
        if result is not None:
            self.VIEWActionResult(result)
