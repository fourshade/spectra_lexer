from .base import ConfigDictionary, ConfigOption, VIEW
from .state import ViewState
from spectra_lexer.resource import StenoIndex
from spectra_lexer.system import CmdlineOption


class ViewManager(VIEW):
    """ Handles GUI interface-based operations. """

    config_file: str = CmdlineOption("config-file", default="~/config.cfg",
                                     desc="CFG file with config settings to load at start and/or write to.")

    show_compound: bool = ConfigOption("board", "compound_keys", default=True,
                                       desc="Show special labels for compound keys (i.e. `f` instead of TP).")
    recursive_graph: bool = ConfigOption("graph", "recursive", default=True,
                                         desc="Include rules that make up other rules.")
    compressed_graph: bool = ConfigOption("graph", "compressed", default=True,
                                          desc="Compress the graph vertically to save space.")
    match_limit: int = ConfigOption("search", "match_limit", default=100,
                                    desc="Maximum number of matches returned on one page of a search.")
    show_links: bool = ConfigOption("search", "example_links", default=True,
                                    desc="Show hyperlinks to other examples of a selected rule from an index.")
    need_all_keys: bool = ConfigOption("search", "need_all_keys", default=False,
                                       desc="Only return lexer results that match every key in the stroke.")

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
        self.VIEWDialogIndexDone()

    def VIEWDialogFileLoad(self, filenames:list, res_type:str) -> None:
        getattr(self, f"RS{res_type.title()}Load")(*filenames)
        self._msg(f"Loaded {res_type} from file dialog.")

    def _msg(self, msg:str) -> None:
        """ Send a message that we've started or finished with an operation. """
        self.SYSStatus(msg)

    def VIEWAction(self, state:dict, action:str="") -> None:
        result = ViewState(state, self).run(action)
        if result is not None:
            self.VIEWActionResult(result)
