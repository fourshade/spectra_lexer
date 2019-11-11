from typing import Any, Dict, List

from .config import ConfigDictionary, ConfigItem, ConfigOption
from .io import ResourceIO
from .steno import StenoEngine


class StenoConfigDictionary(ConfigDictionary):
    """ State attributes that can be user-configured (desktop), or sent in query strings (HTTP). """

    OPTIONS = {"board_compound": ConfigOption("board", "compound_keys", True,
                                              "Show special labels for compound keys (i.e. `f` instead of TP)."),
               "graph_compress": ConfigOption("graph", "compressed_layout", True,
                                              "Compress the graph layout vertically to save space."),
               "graph_compat": ConfigOption("graph", "compatibility_mode", False,
                                            "Force correct spacing in the graph using HTML tables."),
               "match_all_keys": ConfigOption("lexer", "need_all_keys", False,
                                              "Only return lexer results that match every key in the stroke."),
               "matches_per_page": ConfigOption("search", "match_limit", 100,
                                                "Maximum number of matches returned on one page of a search.")}

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        for key, opt in self.OPTIONS.items():
            self.add_option(key, opt)


class StenoApplication:
    """ Common layer for user operations (resource I/O, GUI actions, batch analysis...it all goes through here). """

    def __init__(self, io:ResourceIO, engine:StenoEngine) -> None:
        self._io = io                           # Handles all resource loading, saving, and transcoding.
        self._engine = engine                   # Runtime engine for steno operations such as parsing and graphics.
        self._config = StenoConfigDictionary()  # Keeps track of configuration options in a master dict.
        self._index_file = ""                   # Holds filename for index; set on first load.
        self._config_file = ""                  # Holds filename for config; set on first load.
        self.is_first_run = False               # Set to True if we fail to load the config file.

    def load_translations(self, *filenames:str) -> None:
        """ Load and merge translations from disk. """
        translations = self._io.json_read_merge(*filenames)
        self.set_translations(translations)

    def set_translations(self, translations:Dict[str, str]) -> None:
        """ Send a new translations dict to the engine. """
        self._engine.set_translations(translations)

    def save_translations(self, translations:Dict[str, str], filename:str) -> None:
        """ Save a translations dict directly into JSON. """
        self._io.json_write(translations, filename)

    def load_index(self, filename:str) -> None:
        """ Load an examples index from disk. Ignore missing files. """
        self._index_file = filename
        try:
            index = self._io.json_read(filename)
            self.set_index(index)
        except OSError:
            pass

    def set_index(self, index:Dict[str, dict]) -> None:
        """ Send a new examples index dict to the engine. """
        self._engine.set_index(index)

    def make_index(self, *args, **kwargs) -> None:
        """ Make a index for each built-in rule containing a dict of every translation that used it.
            Finish by setting them active and saving them to disk. """
        index = self._engine.make_index(*args, **kwargs)
        self.set_index(index)
        self.save_index(index)

    def save_index(self, index:Dict[str, dict]) -> None:
        """ Save an examples index structure directly into JSON. """
        assert self._index_file
        self._io.json_write(index, self._index_file)

    def load_config(self, filename:str) -> None:
        """ Load config settings from disk. If the file is missing, set a 'first run' flag and start a new one. """
        self._config_file = filename
        try:
            cfg = self._io.cfg_read(filename)
            self._config.update_from_cfg(cfg)
        except OSError:
            self.is_first_run = True
            self.set_config()

    def set_config(self, options:Dict[str, Any]=None) -> None:
        """ Update the config dict with <options> (if any), and save them to disk. """
        if options:
            self._config.update(options)
        cfg = self._config.to_cfg_sections()
        self.save_config(cfg)

    def save_config(self, cfg:Dict[str, dict]) -> None:
        """ Save a nested config dict into CFG format. """
        assert self._config_file
        self._io.cfg_write(cfg, self._config_file)

    def get_config_info(self) -> List[ConfigItem]:
        """ Return all active config info with formatting instructions. """
        return self._config.info()

    def process_action(self, state:Dict[str, Any], action:str) -> dict:
        """ Perform an <action> on an initial view <state>, then return the changes.
            Config options are added to the view state first. The main state variables may override them. """
        state = {**self._config, **state}
        return self._engine.process_action(state, action)
