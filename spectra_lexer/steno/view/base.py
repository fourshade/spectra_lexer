from typing import Dict, List

from .config import ConfigDictionary, ConfigItem
from .state import ViewState
from ..base import LX

# State attributes that can be user-configured in the GUI version, or sent in query strings in the HTML version.
CONFIG_INFO = [("compound_board", True, "board", "compound_keys",
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
                "Show hyperlinks to indexed examples of selected rules.")]

# Web-specific config options, sent in query strings.
WEB_CONFIG_INFO = [("graph_compat", False, "graph", "compatibility_mode",
                    "Draw the graph using tables (for browsers with poor monospace font support.)")]

# Update the state class with all possible defaults.
ViewState.set_defaults(CONFIG_INFO + WEB_CONFIG_INFO)


class ViewProcessor:

    _engine: LX                # Has access to all outside components.
    _config: ConfigDictionary  # Keeps track of configuration options in a master dict.

    def __init__(self, engine:LX):
        self._engine = engine
        self._config = ConfigDictionary(CONFIG_INFO)

    def load_config(self, cfg:Dict[str, dict]) -> None:
        self._config.sectioned_update(cfg)

    def get_config_info(self) -> ConfigDictionary:
        """ Return formatted config info from all active components. """
        return self._config

    def process(self, state:dict, action:str) -> dict:
        """ Perform an action with the given state dict, then return it with the changes.
            Add config options to the state before processing (but only those the state doesn't already define). """
        d = {**self._config, **state}
        return ViewState(d, self._engine).run(action)
