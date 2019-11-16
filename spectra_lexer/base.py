from configparser import ConfigParser
import json
import os
import sys
from typing import List

from spectra_lexer.app import StenoApplication
from spectra_lexer.cmdline import CmdlineOption, CmdlineOptionNamespace
from spectra_lexer.config import ConfigDictionary
from spectra_lexer.io import AssetPathConverter, CSONLoader, PrefixPathConverter, ResourceIO, UserPathConverter
from spectra_lexer.log import StreamLogger
from spectra_lexer.steno import KeyLayout, RuleCollection, RuleParser, StenoEngineFactory

# The name of this module's root package is used as a default path for built-in assets and user files.
ROOT_PACKAGE = __package__.split(".", 1)[0]
CONVERTER = PrefixPathConverter()
CONVERTER.add(":/", AssetPathConverter(ROOT_PACKAGE))
CONVERTER.add("~/", UserPathConverter(ROOT_PACKAGE))
MAIN_IO = ResourceIO(CONVERTER)


class StenoAppOptions(CmdlineOptionNamespace):
    """ Contains all command-line and config options necessary to build a functioning app object. """

    ASSETS_DIR = ":/assets/"               # Location of built-in assets relative to this package.
    PLOVER_TRANSLATIONS = "$PLOVER_DICTS"  # Sentinel pattern to load the user's Plover dictionaries.

    log_files: str = CmdlineOption("--log", ["~/status.log"], "Text file(s) to log status and exceptions.")
    resource_dir: str = CmdlineOption("--resources", ASSETS_DIR, "Directory with static steno resources.")
    translations_files: list = CmdlineOption("--translations", [PLOVER_TRANSLATIONS],
                                             "JSON translation files to load on start.")
    index_file: str = CmdlineOption("--index", "~/index.json",
                                    "JSON index file to load on start and/or write to.")
    config_file: str = CmdlineOption("--config", "~/config.cfg",
                                     "Config CFG/INI file to load at start and/or write to.")


class StenoAppFactory:
    """ Factory class for an app object. """

    # State attributes that can be user-configured (desktop), or sent in query strings (HTTP).
    CONFIG = [("search_match_limit", 100, "Maximum number of matches returned on one page of a search."),
              ("lexer_strict_mode", False, "Only return lexer results that match every key in a translation."),
              ("graph_compressed_layout", True, "Compress the graph layout vertically to save space."),
              ("graph_compatibility_mode", False, "Force correct spacing in the graph using HTML tables."),
              ("board_compound_key_labels", True, "Show special labels for compound keys (i.e. `f` instead of TP).")]

    def __init__(self, options=StenoAppOptions(), io:ResourceIO=MAIN_IO) -> None:
        self._options = options
        self._io = io
        self._json_load = json.load
        self._cson_load = CSONLoader().load

    def build_logger(self) -> StreamLogger:
        """ Create a logger, which will print non-error messages to stdout by default.
            Open optional files for logging as well (text mode, append to current contents.) """
        logger = StreamLogger()
        logger.add_stream(sys.stdout)
        for filename in self._options.log_files:
            fstream = self._io.open(filename, 'a')
            logger.add_stream(fstream)
        return logger

    def build_app(self) -> StenoApplication:
        """ Load an app with all required resources from this command-line options structure. """
        engine_factory = self.build_factory()
        steno_engine = engine_factory.build_engine()
        config = self.build_config()
        app = StenoApplication(self._io, steno_engine, config)
        translations_files = self._options.translations_files
        if self._options.PLOVER_TRANSLATIONS in translations_files:
            translations_files = self._plover_files()
        if translations_files:
            app.load_translations(*translations_files)
        index_file = self._options.index_file
        if index_file:
            app.load_index(index_file)
        config_file = self._options.config_file
        if config_file:
            app.load_config(config_file)
        return app

    def build_factory(self) -> StenoEngineFactory:
        """ From the base directory, load each steno resource component by a standard name or pattern. """
        layout = self.load_layout()
        rules = self.load_rules()
        rules.make_special(layout.sep, "stroke separator")
        board_defs = self.load_board_defs()
        return StenoEngineFactory(layout, rules, board_defs)

    def build_config(self) -> ConfigDictionary:
        """ Make a blank config dictionary with all option specifications loaded. """
        config = ConfigDictionary()
        for params in self.CONFIG:
            config.add_option(*params)
        return config

    def load_layout(self) -> KeyLayout:
        """ Load a steno key constants structure. """
        with self._open_text_resource("key_layout.json") as fp:
            d = self._json_load(fp)
        return KeyLayout.from_dict(d)

    def load_rules(self) -> RuleCollection:
        """ Load steno rules from every CSON file matching a glob pattern. """
        rules_pattern = self._res_path("[01]*.cson")
        parser = RuleParser()
        for fp in self._io.open_all(rules_pattern, 'r'):
            with fp:
                d = self._cson_load(fp)
            for name, data in d.items():
                parser.add_rule_data(name, data)
        return parser.parse()

    def load_board_defs(self) -> dict:
        """ Load steno board graphics definitions. """
        with self._open_text_resource("board_defs.cson") as fp:
            return self._cson_load(fp)

    def _open_text_resource(self, filename:str):
        """ Open a stream to read a text resource from a relative <filename>. """
        path = self._res_path(filename)
        return self._io.open(path, 'r')

    def _res_path(self, filename:str) -> str:
        """ Return a full path to an asset resource from a relative <filename>. """
        return os.path.join(self._options.resource_dir, filename)

    @staticmethod
    def _plover_files() -> List[str]:
        """ If the sentinel is encountered, search the user's local app data for the Plover config file.
            Parse the dictionaries section and return all dictionary filenames in the correct order. """
        try:
            conv = UserPathConverter("plover")
            path = conv.convert("plover.cfg")
            parser = ConfigParser()
            with open(path, 'r') as fp:
                parser.read_file(fp)
            # Dictionaries are located in the same directory as the config file.
            # The config value we need is read as a string, but it must be decoded as a JSON array.
            value = parser['System: English Stenotype']['dictionaries']
            dict_files = json.loads(value)
            plover_dir = os.path.split(path)[0]
            # Since earlier keys override later ones in Plover, but dict.update does the opposite,
            # we must reverse the priority order before merging.
            return [os.path.join(plover_dir, e['path']) for e in reversed(dict_files)]
        except (IndexError, KeyError, OSError, ValueError):
            # Catch-all for file and parsing errors. The correct files aren't available, so just move on.
            return []
