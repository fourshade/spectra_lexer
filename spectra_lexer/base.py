import os
import sys

from spectra_lexer.analysis import StenoAnalyzer
from spectra_lexer.app import StenoApplication
from spectra_lexer.display import DisplayEngine
from spectra_lexer.engine import StenoEngine
from spectra_lexer.plover import plover_info
from spectra_lexer.resource.board import StenoBoardDefinitions
from spectra_lexer.resource.config import ConfigDictionary
from spectra_lexer.resource.keys import StenoKeyLayout
from spectra_lexer.resource.rules import StenoRuleCollection
from spectra_lexer.search import SearchEngine
from spectra_lexer.util.cmdline import CmdlineOption, CmdlineOptionNamespace
from spectra_lexer.util.json import CSONDecoder
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
    _convert_path = _converter.convert

    CSON_COMMENT_PREFIX = "#"  # Prefix for comments allowed in non-standard JSON files.
    _cson_decoder = CSONDecoder(comment_prefix=CSON_COMMENT_PREFIX)
    _cson_decode = _cson_decoder.decode

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

    def load_app(self, app:StenoApplication) -> None:
        """ Load an app object with all external starting resources. """
        self._load_app_translations(app)
        self._load_app_index(app)
        self._load_app_config(app)

    def _load_app_translations(self, app:StenoApplication) -> None:
        translations_files = self.translations_files
        if self.PLOVER_DICTIONARIES in translations_files:
            translations = plover_info.user_translations(ignore_errors=True)
            app.set_translations(translations)
        elif translations_files:
            app.load_translations(*map(self._convert_path, translations_files))

    def _load_app_index(self, app:StenoApplication) -> None:
        index_file = self.index_file
        if index_file:
            app.load_examples(self._convert_path(index_file, make_dirs=True))

    def _load_app_config(self, app:StenoApplication) -> None:
        config_file = self.config_file
        if config_file:
            app.load_config(self._convert_path(config_file, make_dirs=True))

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

    def _read_cson_resource(self, rel_path:str) -> dict:
        """ Read a resource from a non-standard JSON file under a file path relative to the resources directory. """
        path = os.path.join(self.resource_dir, rel_path)
        filename = self._convert_path(path)
        with open(filename, 'r', encoding='utf-8') as fp:
            s = fp.read()
        return self._cson_decode(s)

    @classmethod
    def main(cls) -> int:
        """ Parse the options and run the application. """
        self = cls()
        self.parse_options()
        return self.run()

    def run(self) -> int:
        """ Run the application. """
        return 0
