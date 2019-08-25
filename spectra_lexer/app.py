import sys
from typing import Any, Dict, List

from .cmdline import Option, OptionNamespace
from .config import ConfigDictionary, ConfigItem
from .log import StreamLogger
from .resource import ResourceLoader
from .state import CONFIG_INFO, ViewState
from .steno import StenoEngine

# The name of this module's root package is used as a default path for built-in assets and user files.
ROOT_PACKAGE = __package__.split(".", 1)[0]


class StenoOptions(OptionNamespace):
    """ Contains all command-line options necessary for a common startup sequence. """
    log_file: str = Option("--log-file", "~/status.log",
                           "Text file to log status and exceptions.")
    resource_dir: str = Option("--resource-dir", ":/assets/",
                               "Directory with static steno resources.")
    translations_files: list = Option("--translations-files", ["~PLOVER/plover.cfg"],
                                      "JSON translation files to load on start.")
    index_file: str = Option("--index-file", "~/index.json",
                             "JSON index file to load on start and/or write to.")
    config_file: str = Option("--config-file", "~/config.cfg",
                              "Config CFG/INI file to load at start and/or write to.")


class StenoApplication:
    """ Primary layer for user operations (resource I/O, GUI actions, batch analysis...it all goes through here.) """

    _res: ResourceLoader       # Handles all resource loading, saving, and transcoding.
    _config: ConfigDictionary  # Keeps track of configuration options in a master dict.
    _logger: StreamLogger      # Logs system events to standard streams and/or files.
    _engine: StenoEngine       # Primary runtime engine for steno operations such as parsing and graphics.

    index_missing: bool = False  # Set to True if we failed to load an index file when asked.

    def __init__(self, opts:StenoOptions=StenoOptions()) -> None:
        """ Load all possible resources from a command-line options structure. """
        self._res = ResourceLoader(ROOT_PACKAGE)
        self._config = ConfigDictionary(CONFIG_INFO)
        self.load_logger(opts.log_file)
        self.log("Loading...")
        self.load_engine(opts.resource_dir)
        self.load_translations(*opts.translations_files)
        self.load_index(opts.index_file)
        self.load_config(opts.config_file)
        self.log("Loading complete.")

    def load_logger(self, filename:str) -> None:
        """ Create the logger, which will print non-error messages to stdout by default. """
        fstream = self._res.open_log_file(filename)
        self._logger = StreamLogger(sys.stdout, fstream)

    def load_engine(self, resource_path:str) -> None:
        """ Create the engine with all steno resource components loaded from a base directory. """
        resources = self._res.load_resources(resource_path)
        self._engine = StenoEngine(*resources)

    def load_translations(self, *filenames:str) -> None:
        """ Load and merge translations from disk. """
        translations = self._res.load_translations(*filenames)
        self.set_translations(translations)

    def set_translations(self, translations:Dict[str, str]) -> None:
        """ Send a new translations dict to the steno engine. """
        self._engine.set_translations(translations)

    def load_index(self, filename:str) -> None:
        """ Load an index from disk. Set a flag if the file is missing. """
        try:
            index = self._res.load_index(filename)
            self.set_index(index, save=False)
        except OSError:
            self.index_missing = True

    def set_index(self, index:Dict[str, dict], *, save:bool=True) -> None:
        """ Send a new index dict to the steno engine and optionally save it to disk. """
        self._engine.set_index(index)
        if save:
            self._res.save_index(index)

    def load_config(self, filename:str) -> None:
        """ Load config settings from disk. Ignore missing files. """
        try:
            cfg = self._res.load_config(filename)
            self._config.sectioned_update(cfg)
        except OSError:
            pass

    def set_config(self, options:Dict[str, Any], *, save:bool=True) -> None:
        """ Update the config dict with these options and optionally save them to disk. """
        self._config.update(options)
        if save:
            cfg = self._config.sectioned_data()
            self._res.save_config(cfg)

    def get_config_info(self) -> List[ConfigItem]:
        """ Return all active config info with formatting instructions. """
        return self._config.info()

    def process_action(self, state:dict, action:str) -> dict:
        """ Perform an action with the given state dict, then return it with the changes.
            Add config options to the state before processing (but only those the state doesn't already define). """
        d = {**self._config, **state}
        return ViewState(d, self._engine).run(action)

    def make_rules(self, filename:str, *args, **kwargs) -> None:
        """ Run the lexer on every item in a JSON steno translations dictionary and save them to <filename>. """
        rules = self._engine.make_rules(*args, **kwargs)
        self._res.save_rules(rules, filename)

    def make_index(self, *args, **kwargs) -> None:
        """ Generate a set of rules from translations using the lexer and compare them to the built-in rules.
            Make a index for each built-in rule containing a dict of every translation that used it.
            Finish by setting them active and saving them to disk. """
        index = self._engine.make_index(*args, **kwargs)
        self.set_index(index, save=True)

    def log(self, message:str) -> None:
        self._logger.log(message)
