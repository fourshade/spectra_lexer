import json
import os
import sys
from typing import List

from spectra_lexer.app import StenoApplication
from spectra_lexer.cmdline import CmdlineOption, CmdlineOptionNamespace
from spectra_lexer.io import AssetPathConverter, PrefixPathConverter, ResourceIO, UserPathConverter
from spectra_lexer.log import StreamLogger
from spectra_lexer.steno import KeyLayout, RuleCollection, RuleParser, StenoEngineFactory

# The name of this module's root package is used as a default path for built-in assets and user files.
ROOT_PACKAGE = __package__.split(".", 1)[0]
CONVERTER = PrefixPathConverter()
CONVERTER.add(":/", AssetPathConverter(ROOT_PACKAGE))
CONVERTER.add("~/", UserPathConverter(ROOT_PACKAGE))
MAIN_IO = ResourceIO(CONVERTER)

CSON_COMMENT_PREFIX = "#"  # Starting character for comments in CSON (commented JSON) files.


class StenoAppOptions(CmdlineOptionNamespace):
    """ Contains all command-line options necessary to build a functioning app object. """

    ASSETS_DIR = ":/assets/"
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

    def __init__(self, options=StenoAppOptions(), io:ResourceIO=MAIN_IO) -> None:
        self._options = options
        self._io = io

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
        app = StenoApplication(self._io, steno_engine)
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
        board_elems = self.load_board_elems()
        return StenoEngineFactory(layout, rules, board_defs, board_elems)

    def load_layout(self) -> KeyLayout:
        """ Load a steno key constants structure. """
        layout_path = self._res_path("layout.json")
        raw_layout = self._json_read(layout_path)
        layout = KeyLayout(**raw_layout)
        layout.verify()
        return layout

    def load_rules(self) -> RuleCollection:
        """ Load steno rules from a CSON glob pattern. """
        rules_pattern = self._res_path("[01]*.cson")
        parser = RuleParser()
        for f in self._io.expand(rules_pattern):
            d = self._cson_read(f)
            for name, data in d.items():
                parser.add_rule_data(name, data)
        return parser.parse()

    def load_board_elems(self) -> dict:
        return self._cson_read(self._res_path("board_elems.cson"))

    def load_board_defs(self) -> dict:
        return self._json_read(self._res_path("board_defs.json"))

    def _json_read(self, filename:str) -> dict:
        """ Read a dict from a standard JSON file. """
        return self._io.json_read(filename)

    def _cson_read(self, filename:str) -> dict:
        """ Read a dict from a non-standard JSON file with full-line comments. """
        return self._io.json_read(filename, comment_prefix=CSON_COMMENT_PREFIX)

    def _res_path(self, filename:str) -> str:
        """ Return a full path to an asset resource from a relative filename. """
        return os.path.join(self._options.resource_dir, filename)

    def _plover_files(self) -> List[str]:
        """ If the sentinel is encountered, search the user's local app data for the Plover config file.
            Parse the dictionaries section and return all dictionary filenames in the correct order. """
        try:
            conv = UserPathConverter("plover")
            path = conv.convert("plover.cfg")
            cfg = self._io.cfg_read(path)
            # Dictionaries are located in the same directory as the config file.
            # The config value we need is read as a string, but it must be decoded as a JSON array.
            value = cfg['System: English Stenotype']['dictionaries']
            dict_files = json.loads(value)
            plover_dir = os.path.split(path)[0]
            # Since earlier keys override later ones in Plover, but dict.update does the opposite,
            # we must reverse the priority order before merging.
            return [os.path.join(plover_dir, e['path']) for e in reversed(dict_files)]
        except (IndexError, KeyError, OSError, ValueError):
            # Catch-all for file and parsing errors. The correct files aren't available, so just move on.
            return []
