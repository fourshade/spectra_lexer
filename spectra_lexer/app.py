import os
import sys
from time import time
from typing import Any, Dict, List

from .base import Main
from .console import SystemConsole
from .io import ResourceIO
from .log import StreamLogger
from .option import CmdlineOption, ConfigDictionary, ConfigItem
from .state import ViewConfig, ViewState
from .steno import IndexInfo, StenoEngine, StenoResources


class StenoApplication:
    """ Common layer for user operations (resource I/O, GUI actions, batch analysis...it all goes through here). """

    def __init__(self, io:ResourceIO, engine:StenoEngine, config:ConfigDictionary) -> None:
        self._io = io               # Handles all resource loading, saving, and transcoding.
        self._engine = engine       # Primary runtime engine for steno operations such as parsing and graphics.
        self._config = config       # Keeps track of configuration options in a master dict.
        self._index_file = ""       # Holds filename for index; set on first load.
        self._config_file = ""      # Holds filename for config; set on first load.
        self.index_missing = False  # Set to True if we fail to load an index file when asked.

    def load_translations(self, *filenames:str) -> None:
        """ Load and merge translations from disk. """
        translations = self._io.load_translations(*filenames)
        self.set_translations(translations)

    def set_translations(self, translations:Dict[str, str]) -> None:
        """ Send a new translations dict to the steno engine. """
        self._engine.set_translations(translations)

    def load_index(self, filename:str) -> None:
        """ Load an index from disk. Set a flag if the file is missing. """
        self._index_file = filename
        try:
            index = self._io.load_index(filename)
            self.set_index(index, save=False)
        except OSError:
            self.index_missing = True

    def set_index(self, index:Dict[str, dict], *, save=True) -> None:
        """ Send a new index dict to the steno engine and optionally save it to disk. """
        self._engine.set_index(index)
        if save:
            self._io.save_index(index, self._index_file)

    def make_rules(self, filename:str, *args, **kwargs) -> None:
        """ Run the lexer on every item in a JSON steno translations dictionary and save the rules to <filename>. """
        raw_rules = self._engine.make_rules(*args, **kwargs)
        self._io.save_rules(raw_rules, filename)

    def make_index(self, *args, **kwargs) -> None:
        """ Generate a set of rules from translations using the lexer and compare them to the built-in rules.
            Make a index for each built-in rule containing a dict of every translation that used it.
            Finish by setting them active and saving them to disk. """
        index = self._engine.make_index(*args, **kwargs)
        self.set_index(index, save=True)

    def load_config(self, filename:str) -> None:
        """ Load config settings from disk. Ignore missing files. """
        self._config_file = filename
        try:
            cfg = self._io.load_config(filename)
            self._config.update_from_cfg(cfg)
        except OSError:
            pass

    def set_config(self, options:Dict[str, Any], *, save=True) -> None:
        """ Update the config dict with these options and optionally save them to disk. """
        self._config.update(options)
        if save:
            cfg = self._config.to_cfg_sections()
            self._io.save_config(cfg, self._config_file)

    def get_config_info(self) -> List[ConfigItem]:
        """ Return all active config info with formatting instructions. """
        return self._config.info()

    def process_action(self, state:dict, action:str) -> dict:
        """ Perform an action with the given state dict, then return it with the changes.
            Add config options to the state before processing (but only those the state doesn't already define). """
        d = {**self._config, **state}
        return ViewState(d, self._engine).run(action)


class StenoMain(Main):
    """ Abstract factory class; contains all command-line options necessary to build a functioning app object. """

    log_files: str = CmdlineOption("--log", ["~/status.log"],
                                   "Text file(s) to log status and exceptions.")
    resource_dir: str = CmdlineOption("--resources", ":/assets/",
                                      "Directory with static steno resources.")
    translations_files: list = CmdlineOption("--translations", ["~PLOVER/plover.cfg"],
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
        logger = StreamLogger(sys.stdout)
        for filename in self.log_files:
            fstream = self._io.open(filename, 'a')
            logger.add_stream(fstream)
        return logger

    def build_app(self, *, with_translations=True, with_index=True, with_config=True) -> StenoApplication:
        """ Load an app with all required resources from this command-line options structure. """
        engine = self.build_engine()
        config = self.build_config()
        app = StenoApplication(self._io, engine, config)
        if with_translations:
            app.load_translations(*self.translations_files)
        if with_index:
            app.load_index(self.index_file)
        if with_config:
            app.load_config(self.config_file)
        return app

    def build_engine(self) -> StenoEngine:
        """ From the base directory, load each steno resource component by a standard name or pattern """
        io = self._io
        layout = io.load_layout(self._res_path("layout.json"))              # Steno key constants.
        rules = io.load_rules(self._res_path("*.cson"))                     # CSON rules glob pattern.
        board_defs = io.load_board_defs(self._res_path("board_defs.json"))  # Board shape definitions.
        board_xml = io.load_board_xml(self._res_path("board_elems.xml"))    # XML steno board elements.
        # Create the engine with all required steno resources.
        resources = StenoResources(layout, rules, board_defs, board_xml)
        return resources.build_engine()

    def build_config(self):
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
        app.make_rules(self.rules_out)


class IndexMain(_BatchMain):
    """ Analyze translations files and create an index from them. """
    index_size: str = CmdlineOption("--size", IndexInfo.DEFAULT_SIZE,
                                    "\n".join(["Relative size of generated index.", *IndexInfo.SIZE_DESCRIPTIONS]))

    def run(self, app:StenoApplication) -> None:
        app.make_index(self.index_size)


console = ConsoleMain()
analyze = AnalyzeMain()
index = IndexMain()
