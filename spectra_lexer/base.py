
import os
import sys

from spectra_lexer.analysis import StenoAnalyzer
from spectra_lexer.app import StenoApplication
from spectra_lexer.display import DisplayEngine
from spectra_lexer.engine import StenoEngine
from spectra_lexer.plover import plover_info
from spectra_lexer.resource.board import StenoBoardDefinitions
from spectra_lexer.resource.config import Configuration
from spectra_lexer.resource.keys import StenoKeyLayout
from spectra_lexer.resource.rules import StenoRuleCollection
from spectra_lexer.search import SearchEngine
from spectra_lexer.util.cmdline import CmdlineOption, CmdlineOptionNamespace
from spectra_lexer.util.json import CSONDecoder
from spectra_lexer.util.log import StreamLogger
from spectra_lexer.util.path import AssetPathConverter, PrefixPathConverter, UserPathConverter

# The name of this module's root package is used as a default path for built-in assets and user files.
ROOT_PACKAGE = __package__.split(".", 1)[0]


class StenoConfiguration(Configuration):

    def __init__(self, *args) -> None:
        """ Add options that can be user-configured (desktop), or sent in query strings (HTTP). """
        super().__init__(*args)
        self.add_option("search_match_limit", 100, "Maximum number of matches returned on one page of a search.")
        self.add_option("lexer_strict_mode", False, "Only return lexer results that match every key in a translation.")
        self.add_option("graph_compressed_layout", True, "Compress the graph layout vertically to save space.")
        self.add_option("graph_compatibility_mode", False, "Force correct spacing in the graph using HTML tables.")


class StenoEngineResources:

    def __init__(self, keymap:StenoKeyLayout, rules:StenoRuleCollection, board_defs:StenoBoardDefinitions) -> None:
        self._keymap = keymap
        self._rules = rules
        self._board_defs = board_defs

    def verify_rules(self) -> None:
        """ Go through each rule and perform integrity checks. """
        valid_keys = self._keymap.valid_rtfcre()
        ignored_keys = self._keymap.dividers()
        for rule in self._rules:
            rule.verify(valid_keys, ignored_keys)

    def build_engine(self) -> StenoEngine:
        search_engine = SearchEngine()
        keymap = self._keymap
        key_parser = keymap.make_parser()
        analyzer = StenoAnalyzer.from_resources(key_parser, self._rules, keymap.sep, keymap.unordered)
        ignored_chars = keymap.split
        combo_key = keymap.unordered[-1:]
        display_engine = DisplayEngine.from_resources(key_parser, self._board_defs, ignored_chars, combo_key)
        return StenoEngine(search_engine, analyzer, display_engine)


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

    LAYOUT_JSON = "key_layout.cson"  # Filename for key layout inside resource directory.
    RULES_CSON = "rules.cson"        # Filename for rules inside resource directory.
    BOARD_CSON = "board_defs.cson"   # Filename for board layout inside resource directory.

    def load_app(self, app:StenoApplication) -> bool:
        """ Load an app object with all external starting resources. """
        self._load_app_translations(app)
        self._load_app_index(app)
        return app.load_config()

    def _load_app_translations(self, app:StenoApplication) -> None:
        filenames = []
        for f in self.translations_files:
            if f == self.PLOVER_DICTIONARIES:
                filenames += plover_info.user_dictionary_files(ignore_errors=True)
            else:
                filenames.append(self._convert_path(f))
        if filenames:
            app.load_translations(*filenames)

    def _load_app_index(self, app:StenoApplication) -> None:
        index_file = self.index_file
        if index_file:
            filename = self._convert_path(index_file, make_dirs=True)
            app.load_examples(filename)

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

    def build_config(self) -> Configuration:
        filename = self._convert_path(self.config_file, make_dirs=True)
        return StenoConfiguration(filename)

    def build_engine(self) -> StenoEngine:
        resources = self._load_resources()
        resources.verify_rules()
        return resources.build_engine()

    def _load_resources(self) -> StenoEngineResources:
        """ From the base directory, load each steno resource component. """
        keymap = self._load_keymap()
        rules = self._load_rules()
        board_defs = self._load_board_defs()
        return StenoEngineResources(keymap, rules, board_defs)

    def _load_keymap(self) -> StenoKeyLayout:
        """ Load a steno key constants structure. """
        d = self._read_cson_resource(self.LAYOUT_JSON)
        return StenoKeyLayout.from_dict(d)

    def _load_rules(self) -> StenoRuleCollection:
        d = self._read_cson_resource(self.RULES_CSON)
        return StenoRuleCollection.from_dict(d)

    def _load_board_defs(self) -> StenoBoardDefinitions:
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
