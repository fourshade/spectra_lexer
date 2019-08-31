import os
import sys
from functools import partial
from time import time
from typing import Any, Dict, List

from .base import IMain, Spectra
from .console import SystemConsole
from .io import ResourceLoader
from .log import StreamLogger
from .option import CmdlineOption, ConfigDictionary, ConfigItem
from .state import ViewConfig, ViewState
from .steno import StenoEngine, StenoResources

# The name of this module's root package is used as a default path for built-in assets and user files.
ROOT_PACKAGE = __package__.split(".", 1)[0]


class StenoApplication:
    """ Common layer for user operations (resource I/O, GUI actions, batch analysis...it all goes through here). """

    def __init__(self, res:ResourceLoader, config:ConfigDictionary, engine:StenoEngine) -> None:
        self._res = res             # Handles all resource loading, saving, and transcoding.
        self._config = config       # Keeps track of configuration options in a master dict.
        self._engine = engine       # Primary runtime engine for steno operations such as parsing and graphics.
        self._index_file = ""       # Holds filename for index; set on first load.
        self._config_file = ""      # Holds filename for config; set on first load.
        self.index_missing = False  # Set to True if we fail to load an index file when asked.

    def load_translations(self, *filenames:str) -> None:
        """ Load and merge translations from disk. """
        translations = self._res.load_translations(*filenames)
        self.set_translations(translations)

    def set_translations(self, translations:Dict[str, str]) -> None:
        """ Send a new translations dict to the steno engine. """
        self._engine.set_translations(translations)

    def load_index(self, filename:str) -> None:
        """ Load an index from disk. Set a flag if the file is missing. """
        self._index_file = filename
        try:
            index = self._res.load_index(filename)
            self.set_index(index, save=False)
        except OSError:
            self.index_missing = True

    def set_index(self, index:Dict[str, dict], *, save=True) -> None:
        """ Send a new index dict to the steno engine and optionally save it to disk. """
        self._engine.set_index(index)
        if save:
            self._res.save_index(index, self._index_file)

    def load_config(self, filename:str) -> None:
        """ Load config settings from disk. Ignore missing files. """
        self._config_file = filename
        try:
            cfg = self._res.load_config(filename)
            self._config.update_from_cfg(cfg)
        except OSError:
            pass

    def set_config(self, options:Dict[str, Any], *, save=True) -> None:
        """ Update the config dict with these options and optionally save them to disk. """
        self._config.update(options)
        if save:
            cfg = self._config.to_cfg_sections()
            self._res.save_config(cfg, self._config_file)

    def get_config_info(self) -> List[ConfigItem]:
        """ Return all active config info with formatting instructions. """
        return self._config.info()

    def process_action(self, state:dict, action:str) -> dict:
        """ Perform an action with the given state dict, then return it with the changes.
            Add config options to the state before processing (but only those the state doesn't already define). """
        d = {**self._config, **state}
        return ViewState(d, self._engine).run(action)

    def make_rules(self, filename:str, *args, **kwargs) -> None:
        """ Run the lexer on every item in a JSON steno translations dictionary and save the rules to <filename>. """
        raw_rules = self._engine.make_rules(*args, **kwargs)
        self._res.save_rules(raw_rules, filename)

    def make_index(self, *args, **kwargs) -> None:
        """ Generate a set of rules from translations using the lexer and compare them to the built-in rules.
            Make a index for each built-in rule containing a dict of every translation that used it.
            Finish by setting them active and saving them to disk. """
        index = self._engine.make_index(*args, **kwargs)
        self.set_index(index, save=True)


class StenoMain(IMain):
    """ Abstract factory class; contains all command-line options necessary to build a functioning app object. """

    log_file: str = CmdlineOption("--log-file", "~/status.log",
                                  "Text file to log status and exceptions.")
    resource_dir: str = CmdlineOption("--resource-dir", ":/assets/",
                                      "Directory with static steno resources.")
    translations_files: list = CmdlineOption("--translations-files", ["~PLOVER/plover.cfg"],
                                             "JSON translation files to load on start.")
    index_file: str = CmdlineOption("--index-file", "~/index.json",
                                    "JSON index file to load on start and/or write to.")
    config_file: str = CmdlineOption("--config-file", "~/config.cfg",
                                     "Config CFG/INI file to load at start and/or write to.")

    def __init__(self) -> None:
        self._res = ResourceLoader(ROOT_PACKAGE, ROOT_PACKAGE)

    def build_app(self, *, with_translations=True, with_index=True, with_config=True) -> StenoApplication:
        """ Load an app with all required resources from this command-line options structure. """
        res = self._res
        config = ConfigDictionary()
        config.add_options(ViewConfig())
        # From the base directory, load each steno resource component by a standard name or pattern.
        with_path = partial(os.path.join, self.resource_dir)
        layout = res.load_layout(with_path("layout.json"))              # Steno key constants.
        rules = res.load_rules(with_path("*.cson"))                     # CSON rules glob pattern.
        board_defs = res.load_board_defs(with_path("board_defs.json"))  # Board shape definitions.
        board_xml = res.load_board_xml(with_path("board_elems.xml"))    # XML steno board elements.
        # Create the engine with all required steno resources.
        resources = StenoResources(layout, rules, board_defs, board_xml)
        engine = resources.build_engine()
        app = StenoApplication(res, config, engine)
        if with_translations:
            app.load_translations(*self.translations_files)
        if with_index:
            app.load_index(self.index_file)
        if with_config:
            app.load_config(self.config_file)
        return app

    def build_logger(self, *, with_file=True) -> StreamLogger:
        """ Create the logger, which will print non-error messages to stdout by default.
            Open an optional file for logging as well (text mode, append to current contents.) """
        logger = StreamLogger(sys.stdout)
        if with_file:
            fstream = self._res.open(self.log_file, 'a')
            logger.add_stream(fstream)
        return logger


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
    rules_out: str = CmdlineOption("--rules-out", "./rules.json", "Output file name for lexer-generated rules.")

    def run(self, app:StenoApplication) -> None:
        app.make_rules(self.rules_out)


class IndexMain(_BatchMain):
    """ Analyze translations files and create an index from them. """

    def run(self, app:StenoApplication) -> None:
        app.make_index()


# Module for console and batch operations. Not very popular...
console = Spectra(ConsoleMain)
analyze = Spectra(AnalyzeMain)
index = Spectra(IndexMain)
