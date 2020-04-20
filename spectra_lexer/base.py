import os
import sys

from spectra_lexer.analysis import StenoAnalyzer
from spectra_lexer.display import BoardFactory, GraphFactory
from spectra_lexer.engine import StenoEngine
from spectra_lexer.plover import plover_info
from spectra_lexer.resource.board import StenoBoardDefinitions
from spectra_lexer.resource.keys import StenoKeyLayout
from spectra_lexer.resource.rules import StenoRuleCollection
from spectra_lexer.search import SearchEngine
from spectra_lexer.util.cmdline import CmdlineOptions
from spectra_lexer.util.json import CSONDecoder
from spectra_lexer.util.log import StreamLogger
from spectra_lexer.util.path import AssetPathConverter, PrefixPathConverter, UserPathConverter

# The name of this module's root package is used as a default path for built-in assets and user files.
ROOT_PACKAGE = __package__.split(".", 1)[0]


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
        keymap = self._keymap
        key_parser = keymap.make_parser()
        search_engine = SearchEngine()
        analyzer = StenoAnalyzer.from_resources(key_parser, self._rules, keymap.sep, keymap.unordered)
        node_factory = GraphFactory(keymap.split)
        board_factory = BoardFactory.from_resources(key_parser,self._board_defs, keymap.unordered[-1:])
        return StenoEngine(search_engine, analyzer, node_factory, board_factory)


class Spectra:
    """ Main factory class. Contains all command-line options necessary to build a functioning engine and app. """

    ASSET_PATH_PREFIX = ":/"           # Prefix that indicates built-in assets.
    USER_PATH_PREFIX = "~/"            # Prefix that indicates local user app data.
    PLOVER_SENTINEL = "$PLOVER_DICTS"  # Sentinel pattern to load the user's Plover dictionaries.
    CSON_COMMENT_PREFIX = "#"        # Prefix for comments allowed in non-standard JSON files.
    LAYOUT_CSON = "key_layout.cson"  # Filename for key layout inside resource directory.
    RULES_CSON = "rules.cson"        # Filename for rules inside resource directory.
    BOARD_CSON = "board_defs.cson"   # Filename for board layout inside resource directory.

    def __init__(self, opts:CmdlineOptions=None) -> None:
        """ Parse any command-line options, then create the logger.
            It will print messages to stdout and to a file (text mode, append to current contents.)
            Create empty directories if necessary. Log files will remain open until program close. """
        if opts is None:
            opts = CmdlineOptions("Running Spectra as a library (should never be seen).")
        opts.add("log", self.USER_PATH_PREFIX + "status.log",
                 "Text file to log status and exceptions.")
        opts.add("resources", self.ASSET_PATH_PREFIX + "assets/",
                 "Directory with static steno resources.")
        opts.add("translations", [self.PLOVER_SENTINEL],
                 "JSON translation files to load on start.")
        opts.add("index", self.USER_PATH_PREFIX + "index.json",
                 "JSON index file to load on start and/or write to.")
        opts.add("config", Spectra.USER_PATH_PREFIX + "config.cfg",
                 "Config CFG/INI file to load at start and/or write to.")
        opts.parse()
        converter = PrefixPathConverter()
        converter.add(self.ASSET_PATH_PREFIX, AssetPathConverter(ROOT_PACKAGE))
        converter.add(self.USER_PATH_PREFIX, UserPathConverter(ROOT_PACKAGE))
        log_path = converter.convert(opts.log, make_dirs=True)
        log_stream = open(log_path, 'a', encoding='utf-8')
        logger = StreamLogger()
        logger.add_stream(sys.stdout)
        logger.add_stream(log_stream)
        self.log = logger.log
        self._convert_path = converter.convert
        self._cson_decoder = CSONDecoder(comment_prefix=self.CSON_COMMENT_PREFIX)
        self._opts = opts

    def _read_cson_resource(self, rel_path:str) -> dict:
        """ Read a resource from a non-standard JSON file under a file path relative to the resources directory. """
        path = os.path.join(self._opts.resources, rel_path)
        filename = self._convert_path(path)
        with open(filename, 'r', encoding='utf-8') as fp:
            s = fp.read()
        return self._cson_decoder.decode(s)

    def _load_resources(self) -> StenoEngineResources:
        """ From the base directory, load each steno resource component. """
        keymap = self._load_keymap()
        rules = self._load_rules()
        board_defs = self._load_board_defs()
        return StenoEngineResources(keymap, rules, board_defs)

    def _load_keymap(self) -> StenoKeyLayout:
        """ Load a steno key constants structure. """
        d = self._read_cson_resource(self.LAYOUT_CSON)
        return StenoKeyLayout.from_dict(d)

    def _load_rules(self) -> StenoRuleCollection:
        d = self._read_cson_resource(self.RULES_CSON)
        return StenoRuleCollection.from_dict(d)

    def _load_board_defs(self) -> StenoBoardDefinitions:
        """ Load a dict with steno board graphics definitions. """
        d = self._read_cson_resource(self.BOARD_CSON)
        return StenoBoardDefinitions(d)

    def translations_paths(self) -> list:
        filenames = []
        for f in self._opts.translations:
            if f == self.PLOVER_SENTINEL:
                filenames += plover_info.user_dictionary_files(ignore_errors=True)
            else:
                filenames.append(self._convert_path(f))
        return filenames

    def index_path(self) -> str:
        path = self._opts.index
        return self._convert_path(path, make_dirs=True)

    def config_path(self) -> str:
        path = self._opts.config
        return self._convert_path(path, make_dirs=True)

    def build_engine(self) -> StenoEngine:
        resources = self._load_resources()
        resources.verify_rules()
        return resources.build_engine()
