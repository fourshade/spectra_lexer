from configparser import ConfigParser
import json
import os
import sys
from typing import List

from spectra_lexer.analysis import StenoAnalyzer
from spectra_lexer.app import StenoApplication
from spectra_lexer.display import DisplayEngine
from spectra_lexer.engine import StenoEngine
from spectra_lexer.resource import ConfigDictionary, RTFCREDict, StenoBoardDefinitions, StenoKeyLayout, \
    StenoRuleCollection
from spectra_lexer.search import SearchEngine
from spectra_lexer.util.cmdline import CmdlineOption, CmdlineOptionNamespace
from spectra_lexer.util.log import StreamLogger
from spectra_lexer.util.path import AssetPathConverter, PrefixPathConverter, UserPathConverter

# The name of this module's root package is used as a default path for built-in assets and user files.
ROOT_PACKAGE = __package__.split(".", 1)[0]


class StenoEngineFactory:
    """ Sub-factory for the steno engine itself. """

    def __init__(self, keymap:StenoKeyLayout, rules:StenoRuleCollection, board_defs:StenoBoardDefinitions) -> None:
        self._keymap = keymap
        self._rules = rules
        self._board_defs = board_defs

    @staticmethod
    def build_search_engine() -> SearchEngine:
        return SearchEngine()

    def build_analyzer(self) -> StenoAnalyzer:
        keymap = self._keymap
        key_parser = keymap.make_parser()
        return StenoAnalyzer.from_resources(key_parser, self._rules, keymap.sep, keymap.unordered)

    def build_display_engine(self) -> DisplayEngine:
        keymap = self._keymap
        key_parser = keymap.make_parser()
        ignored_chars = keymap.split
        combo_key = keymap.unordered[-1:]
        return DisplayEngine.from_resources(key_parser, self._board_defs, ignored_chars, combo_key)


class Spectra(CmdlineOptionNamespace):
    """ Main factory class. Contains all command-line options necessary to build a functioning engine and app. """

    _converter = PrefixPathConverter()
    _converter.add(":/", AssetPathConverter(ROOT_PACKAGE))  # Prefix indicates built-in assets.
    _converter.add("~/", UserPathConverter(ROOT_PACKAGE))   # Prefix indicates local user app data.

    CSON_COMMENT_PREFIX = "#"              # Prefix for comments allowed in non-standard JSON files.
    PLOVER_DICTIONARIES = "$PLOVER_DICTS"  # Sentinel pattern to load the user's Plover dictionaries.

    log_files: str = CmdlineOption("--log", ["~/status.log"], "Text file(s) to log status and exceptions.")
    resource_dir: str = CmdlineOption("--resources", ":/assets/", "Directory with static steno resources.")
    translations_files: list = CmdlineOption("--translations", [PLOVER_DICTIONARIES],
                                             "JSON translation files to load on start.")
    index_file: str = CmdlineOption("--index", "~/index.json",
                                    "JSON index file to load on start and/or write to.")
    config_file: str = CmdlineOption("--config", "~/config.cfg",
                                     "Config CFG/INI file to load at start and/or write to.")

    # Options that can be user-configured (desktop), or sent in query strings (HTTP).
    CONFIG = [("search_match_limit",        100,   "Maximum number of matches returned on one page of a search."),
              ("lexer_strict_mode",         False, "Only return lexer results that match every key in a translation."),
              ("graph_compressed_layout",   True,  "Compress the graph layout vertically to save space."),
              ("graph_compatibility_mode",  False, "Force correct spacing in the graph using HTML tables.")]

    LAYOUT_JSON = "key_layout.cson"  # Filename for key layout inside resource directory.
    RULES_CSON = "rules.cson"        # Filename for rules inside resource directory.
    BOARD_CSON = "board_defs.cson"   # Filename for board layout inside resource directory.

    PLOVER_APP = "plover"            # Name of Plover application for finding its user data folder.
    PLOVER_CFG = "plover.cfg"        # Filename for Plover configuration with user dictionaries.

    def load_app(self, app:StenoApplication) -> None:
        """ Load an app object with all external starting resources. """
        translations_files = self.translations_files
        if self.PLOVER_DICTIONARIES in translations_files:
            translations = self._plover_translations()
            app.set_translations(translations)
        elif translations_files:
            app.load_translations(*map(self._convert_path, translations_files))
        index_file = self.index_file
        if index_file:
            app.load_examples(self._convert_path(index_file, make_dirs=True))
        config_file = self.config_file
        if config_file:
            app.load_config(self._convert_path(config_file, make_dirs=True))

    def _plover_translations(self) -> RTFCREDict:
        """ Search the user's local app data for the Plover config file, find the dictionaries, and load them. """
        filenames = self._find_plover_dictionaries()
        return RTFCREDict.from_json_files(*filenames)

    def build_logger(self) -> StreamLogger:
        """ Create a logger, which will print non-error messages to stdout by default.
            Open optional files for logging as well (text mode, append to current contents.)
            Create empty directories if necessary. Log files will remain open until program close. """
        logger = StreamLogger()
        logger.add_stream(sys.stdout)
        for path in self.log_files:
            filename = self._convert_path(path, make_dirs=True)
            fstream = open(filename, 'a', encoding='utf-8')
            logger.add_stream(fstream)
        return logger

    def build_app(self) -> StenoApplication:
        """ Build an app with all required resources from this object's command-line options. """
        config = self.build_config()
        engine = self.build_engine()
        return StenoApplication(config, engine)

    def build_config(self) -> ConfigDictionary:
        config = ConfigDictionary()
        for params in self.CONFIG:
            config.add_option(*params)
        return config

    def build_engine(self) -> StenoEngine:
        factory = self.build_factory()
        search_engine = factory.build_search_engine()
        analyzer = factory.build_analyzer()
        display_engine = factory.build_display_engine()
        return StenoEngine(search_engine, analyzer, display_engine)

    def build_factory(self) -> StenoEngineFactory:
        """ From the base directory, load each steno resource component and set up the main factory. """
        keymap = self.load_keymap()
        rules = self.load_rules()
        board_defs = self.load_board_defs()
        return StenoEngineFactory(keymap, rules, board_defs)

    def load_keymap(self) -> StenoKeyLayout:
        """ Load a steno key constants structure. """
        d = self._read_cson_resource(self.LAYOUT_JSON)
        return StenoKeyLayout.from_dict(d)

    def load_rules(self) -> StenoRuleCollection:
        d = self._read_cson_resource(self.RULES_CSON)
        return StenoRuleCollection.from_dict(d)

    def load_board_defs(self) -> StenoBoardDefinitions:
        """ Load a dict with steno board graphics definitions. """
        d = self._read_cson_resource(self.BOARD_CSON)
        return StenoBoardDefinitions(d)

    def _convert_path(self, path:str, *, make_dirs=False) -> str:
        """ Convert a specially formatted path string into a full file path usable by open().
            If <make_dirs> is true, create directories as needed to make the path exist. """
        file_path = self._converter.convert(path)
        if make_dirs:
            directory = os.path.dirname(file_path) or "."
            os.makedirs(directory, exist_ok=True)
        return file_path

    def _read_cson_resource(self, rel_path:str) -> dict:
        """ Read a resource from a non-standard JSON file under a file path relative to the resources directory. """
        path = os.path.join(self.resource_dir, rel_path)
        path = self._convert_path(path)
        return self._cson_read(path)

    def _cson_read(self, filename:str) -> dict:
        """ Read an object from a non-standard JSON file stream with full-line comments (CSON = commented JSON).
            JSON doesn't care about leading or trailing whitespace anyway, so strip every line first. """
        with open(filename, 'r', encoding='utf-8') as fp:
            stripped_line_iter = map(str.strip, fp)
            data_lines = [line for line in stripped_line_iter
                          if line and not line.startswith(self.CSON_COMMENT_PREFIX)]
            data = "\n".join(data_lines)
            return json.loads(data)

    def _find_plover_dictionaries(self, *, ignore_errors=True) -> List[str]:
        """ Search the user's local app data for the Plover config file.
            Parse the dictionaries section and return the filenames for all dictionaries in order. """
        try:
            converter = UserPathConverter(self.PLOVER_APP)
            cfg_filename = converter.convert(self.PLOVER_CFG)
            parser = ConfigParser()
            with open(cfg_filename, 'r', encoding='utf-8') as fp:
                parser.read_file(fp)
            # Dictionaries are located in the same directory as the config file.
            # The config value we need is read as a string, but it must be decoded as a JSON array of objects.
            value = parser['System: English Stenotype']['dictionaries']
            dictionary_specs = json.loads(value)
            plover_dir = os.path.split(cfg_filename)[0]
            # Earlier keys override later ones in Plover, but dict.update does the opposite. Reverse the priority order.
            return [os.path.join(plover_dir, spec['path']) for spec in reversed(dictionary_specs)]
        except (IndexError, KeyError, OSError, ValueError):
            # Catch-all for file and parsing errors. Return an empty list if <ignore_errors> is True.
            if not ignore_errors:
                raise
            return []

    @classmethod
    def main(cls) -> int:
        """ Parse the options and run the application. """
        self = cls()
        self.parse_options(app_description=str(cls.__doc__))
        return self.run()

    def run(self) -> int:
        """ Run the application. """
        return 0
