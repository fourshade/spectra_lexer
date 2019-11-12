import os
import sys

from spectra_lexer.app import StenoApplication
from spectra_lexer.cmdline import CmdlineOption, CmdlineOptionNamespace
from spectra_lexer.io import StenoResourceIO
from spectra_lexer.log import StreamLogger
from spectra_lexer.steno import KeyLayout, RuleCollection, RuleParser, StenoEngineFactory


class StenoAppOptions(CmdlineOptionNamespace):
    """ Contains all command-line options necessary to build a functioning app object. """

    ASSETS_DIR = ":/assets/"

    log_files: str = CmdlineOption("--log", ["~/status.log"], "Text file(s) to log status and exceptions.")
    resource_dir: str = CmdlineOption("--resources", ASSETS_DIR, "Directory with static steno resources.")
    translations_files: list = CmdlineOption("--translations", [StenoResourceIO.PLOVER_TRANSLATIONS],
                                             "JSON translation files to load on start.")
    index_file: str = CmdlineOption("--index", "~/index.json",
                                    "JSON index file to load on start and/or write to.")
    config_file: str = CmdlineOption("--config", "~/config.cfg",
                                     "Config CFG/INI file to load at start and/or write to.")


class StenoAppFactory:
    """ Abstract factory class for an app object. """

    def __init__(self, options=StenoAppOptions()) -> None:
        self._options = options
        self._io = StenoResourceIO()

    def build_logger(self) -> StreamLogger:
        """ Create a logger, which will print non-error messages to stdout by default.
            Open optional files for logging as well (text mode, append to current contents.) """
        logger = StreamLogger()
        logger.add_stream(sys.stdout)
        for filename in self._options.log_files:
            fstream = self._io.open(filename, 'a')
            logger.add_stream(fstream)
        return logger

    def build_app(self, *, with_translations=True, with_index=True, with_config=True) -> StenoApplication:
        """ Load an app with all required resources from this command-line options structure. """
        engine_factory = self.build_factory()
        steno_engine = engine_factory.build_engine()
        app = StenoApplication(self._io, steno_engine)
        if with_translations:
            app.load_translations(*self._options.translations_files)
        if with_index:
            app.load_index(self._options.index_file)
        if with_config:
            app.load_config(self._options.config_file)
        return app

    def build_factory(self) -> StenoEngineFactory:
        """ From the base directory, load each steno resource component by a standard name or pattern. """
        layout = self.load_layout()
        rules = self.load_rules()
        rules.make_special(layout.sep, "stroke separator")
        board_defs = self._io.json_read(self._res_path("board_defs.json"))
        board_elems = self._io.cson_read(self._res_path("board_elems.cson"))
        return StenoEngineFactory(layout, rules, board_defs, board_elems)

    def load_layout(self) -> KeyLayout:
        """ Load a steno key constants structure. """
        raw_layout = self._io.json_read(self._res_path("layout.json"))
        layout = KeyLayout(**raw_layout)
        layout.verify()
        return layout

    def load_rules(self) -> RuleCollection:
        """ Load steno rules from a CSON glob pattern. """
        raw_rules = self._io.cson_read_merge(self._res_path("[01]*.cson"), check_keys=True)
        parser = RuleParser(raw_rules)
        rule_iter = parser.parse()
        return RuleCollection(rule_iter)

    def _res_path(self, filename:str) -> str:
        """ Return a full path to an asset resource from a relative filename. """
        return os.path.join(self._options.resource_dir, filename)
