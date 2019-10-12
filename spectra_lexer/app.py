import os
import sys
from time import time
from typing import Any, Dict, List

from .base import Main
from .console import SystemConsole
from .io import ResourceIO
from .log import StreamLogger
from .option import CmdlineOption, ConfigDictionary, ConfigItem
from .search import ExampleIndexInfo, SearchEngine
from .state import ViewConfig, ViewState
from .steno import StenoEngine, StenoResources


class StenoApplication:
    """ Common layer for user operations (resource I/O, GUI actions, batch analysis...it all goes through here). """

    def __init__(self, io:ResourceIO, steno_engine:StenoEngine,
                 search_engine:SearchEngine, config:ConfigDictionary) -> None:
        self._io = io                        # Handles all resource loading, saving, and transcoding.
        self._steno_engine = steno_engine    # Runtime engine for steno operations such as parsing and graphics.
        self._search_engine = search_engine  # Runtime engine for translation search operations.
        self._config = config                # Keeps track of configuration options in a master dict.
        self._index_file = ""                # Holds filename for index; set on first load.
        self._config_file = ""               # Holds filename for config; set on first load.
        self.is_first_run = False            # Set to True if we fail to load the config file.

    def load_translations(self, *filenames:str) -> None:
        """ Load and merge translations from disk. """
        translations = self._io.json_read_merge(*filenames)
        self.set_translations(translations)

    def set_translations(self, translations:Dict[str, str]) -> None:
        """ Send a new translations dict to the search engine and keep a copy for bulk analysis. """
        self._search_engine.set_translations(translations)

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
        """ Send a new examples index dict to the search engine. """
        self._search_engine.set_index(index)

    def save_index(self, index:Dict[str, dict]) -> None:
        """ Save an examples index structure directly into JSON. """
        assert self._index_file
        self._io.json_write(index, self._index_file)

    def make_rules(self, filename:str, **kwargs) -> None:
        """ Run the lexer on every item in the steno translations dictionary and save the rules to <filename>. """
        translations = self._search_engine.get_translations()
        raw_rules = self._steno_engine.make_rules(translations, **kwargs)
        self._io.json_write(raw_rules, filename)

    def make_index(self, size:int, **kwargs) -> None:
        """ Make a index for each built-in rule containing a dict of every translation that used it.
            Use an input filter to control size. Finish by setting them active and saving them to disk. """
        translations = self._search_engine.get_filtered_translations(size)
        index = self._steno_engine.make_index(translations, **kwargs)
        self.set_index(index)
        self.save_index(index)

    def get_index_info(self) -> ExampleIndexInfo:
        """ Return information about creating a new example index. """
        return self._search_engine.get_index_info()

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
        assert self._config_file
        if options:
            self._config.update(options)
        cfg = self._config.to_cfg_sections()
        self._io.cfg_write(cfg, self._config_file)

    def get_config_info(self) -> List[ConfigItem]:
        """ Return all active config info with formatting instructions. """
        return self._config.info()

    def process_action(self, state:Dict[str, Any], action:str) -> dict:
        """ Perform an <action> on an initial view <state>, then return the changes.
            Config options are added to the view state first. The main state variables may override them. """
        view_state = ViewState(self._steno_engine, self._search_engine)
        view_state.update(self._config)
        view_state.update(state)
        view_state.run(action)
        return view_state.get_modified()


class StenoMain(Main):
    """ Abstract factory class; contains all command-line options necessary to build a functioning app object. """

    log_files: str = CmdlineOption("--log", ["~/status.log"],
                                   "Text file(s) to log status and exceptions.")
    resource_dir: str = CmdlineOption("--resources", ":/assets/",
                                      "Directory with static steno resources.")
    translations_files: list = CmdlineOption("--translations", [ResourceIO.PLOVER_TRANSLATIONS],
                                             "JSON translation files to load on start.")
    index_file: str = CmdlineOption("--index", "~/index.json",
                                    "JSON index file to load on start and/or write to.")
    config_file: str = CmdlineOption("--config", "~/config.cfg",
                                     "Config CFG/INI file to load at start and/or write to.")

    def __init__(self) -> None:
        self._io = ResourceIO()

    def build_logger(self) -> StreamLogger:
        """ Create a logger, which will print non-error messages to stdout by default.
            Open optional files for logging as well (text mode, append to current contents.) """
        logger = StreamLogger()
        logger.add_stream(sys.stdout)
        for filename in self.log_files:
            fstream = self._io.open(filename, 'a')
            logger.add_stream(fstream)
        return logger

    def build_app(self, *, with_translations=True, with_index=True, with_config=True) -> StenoApplication:
        """ Load an app with all required resources from this command-line options structure. """
        resources = self.build_resources()
        steno_engine = resources.build_engine()
        search_engine = SearchEngine()
        config = self.build_config()
        app = StenoApplication(self._io, steno_engine, search_engine, config)
        if with_translations:
            app.load_translations(*self.translations_files)
        if with_index:
            app.load_index(self.index_file)
        if with_config:
            app.load_config(self.config_file)
        return app

    def build_resources(self) -> StenoResources:
        """ From the base directory, load each steno resource component by a standard name or pattern. """
        io = self._io
        layout = io.json_read(self._res_path("layout.json"))                       # Steno key constants.
        rules = io.cson_read_merge(self._res_path("[01]*.cson"), check_keys=True)  # CSON rules glob pattern.
        board_defs = io.json_read(self._res_path("board_defs.json"))               # Board shape definitions.
        board_elems = io.cson_read(self._res_path("board_elems.cson"))             # Board elements definitions.
        return StenoResources(layout, rules, board_defs, board_elems)

    @staticmethod
    def build_config() -> ConfigDictionary:
        """ Create the config dict from the GUI state options. """
        config = ConfigDictionary()
        config.add_options(ViewConfig())
        return config

    def _res_path(self, filename:str) -> str:
        """ Return a full path to a built-in asset resource from a relative filename. """
        return os.path.join(self.resource_dir, filename)


class ConsoleMain(StenoMain):
    """ Run an interactive read-eval-print loop in a new console with the app vars as the namespace. """

    def main(self) -> int:
        logger = self.build_logger()
        logger.log("Loading...")
        app = self.build_app()
        logger.log("Loading complete.")
        SystemConsole(vars(app)).repl()
        return 0


class _BatchMain(StenoMain):
    """ Abstract class; adds batch timing capabilities. """

    processes: int = CmdlineOption("--processes", 0, "Number of processes used for parallel execution.")

    def main(self) -> int:
        """ Run a batch operation and time its execution. """
        start_time = time()
        logger = self.build_logger()
        logger.log("Operation started...")
        app = self.build_app()
        self.run(app)
        total_time = time() - start_time
        logger.log(f"Operation done in {total_time:.1f} seconds.")
        return 0

    def run(self, app:StenoApplication) -> None:
        raise NotImplementedError


class AnalyzeMain(_BatchMain):
    """ Run the lexer on every item in a JSON steno translations dictionary. """

    # As part of the built-in resource block, rules have no default save location, so add one.
    rules_out: str = CmdlineOption("--out", "./rules.json", "JSON output file name for lexer-generated rules.")

    def run(self, app:StenoApplication) -> None:
        app.make_rules(self.rules_out, processes=self.processes)


class IndexMain(_BatchMain):
    """ Analyze translations files and create an index from them. """

    _INFO = SearchEngine.get_index_info()
    index_size: int = CmdlineOption("--size", _INFO.default_size(),
                                    "\n".join(["Relative size of generated index.", *_INFO.size_descriptions()]))

    def run(self, app:StenoApplication) -> None:
        app.make_index(self.index_size, processes=self.processes)


console = ConsoleMain()
analyze = AnalyzeMain()
index = IndexMain()
