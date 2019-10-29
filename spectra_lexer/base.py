import os
import sys

from spectra_lexer.app import StenoApplication
from spectra_lexer.io import ResourceIO
from spectra_lexer.log import StreamLogger
from spectra_lexer.option import CmdlineOption, CmdlineParser
from spectra_lexer.search import SearchEngine
from spectra_lexer.steno import KeyLayout, RuleParser, StenoEngine, StenoEngineFactory


class Main:
    """ Abstract base class for a main application entry point. It is meant to contain application options.
        Typically, there will be a number of "Option" objects in the class namespace. These will be
        examined and added to a parser, which will take the command-line arguments and overwrite any
        attributes on the instance that match. Defaults will take over for options with no matches. """

    def __call__(self, script:str="", *argv:str) -> int:
        """ Create a parser object, load command line options into it, and call the main entry point function. """
        parser = CmdlineParser()
        for tp in self.__class__.__mro__[::-1]:
            for attr, item in vars(tp).items():
                if isinstance(item, CmdlineOption):
                    parser.add_option(attr, item)
        parser.add_help(script, self.__doc__ or "")
        opt_dict = parser.parse(argv)
        self.__dict__.update(opt_dict)
        return self.main()

    def main(self) -> int:
        """ Main entry point; returns an int as an exit code. """
        raise NotImplementedError


class StenoMain(Main):
    """ Abstract factory class; contains all command-line options necessary to build a functioning app object. """

    log_files: str = CmdlineOption("--log", ["~/status.log"],
                                   "Text file(s) to log status and exceptions.")
    resource_dir: str = CmdlineOption("--resources", ":/assets/",
                                      "Directory with static steno resources.")
    translations_files: list = CmdlineOption("--translations", [ResourceIO.PLOVER_TRANSLATIONS],
                                             "JSON translation files to load on start.")
    index_file: str = CmdlineOption("--index", "~/index.json",
                                    "JSON index file to load on start and/or write to.")
    config_file: str = CmdlineOption("--config", "~/config.cfg",
                                     "Config CFG/INI file to load at start and/or write to.")

    def build_logger(self) -> StreamLogger:
        """ Create a logger, which will print non-error messages to stdout by default.
            Open optional files for logging as well (text mode, append to current contents.) """
        io = ResourceIO()
        logger = StreamLogger()
        logger.add_stream(sys.stdout)
        for filename in self.log_files:
            fstream = io.open(filename, 'a')
            logger.add_stream(fstream)
        return logger

    def build_app(self, *, with_translations=True, with_index=True, with_config=True) -> StenoApplication:
        """ Load an app with all required resources from this command-line options structure. """
        io = ResourceIO()
        factory = self.build_factory(io)
        lexer = factory.build_lexer()
        board_engine = factory.build_board_engine()
        graph_engine = factory.build_graph_engine()
        captions = factory.build_captions()
        steno_engine = StenoEngine(factory.layout, lexer, board_engine, graph_engine, captions)
        search_engine = SearchEngine()
        app = StenoApplication(io, steno_engine, search_engine)
        if with_translations:
            app.load_translations(*self.translations_files)
        if with_index:
            app.load_index(self.index_file)
        if with_config:
            app.load_config(self.config_file)
        return app

    def build_factory(self, io:ResourceIO) -> StenoEngineFactory:
        """ From the base directory, load each steno resource component by a standard name or pattern. """
        raw_layout = io.json_read(self._res_path("layout.json"))                       # Steno key constants.
        layout = KeyLayout(**raw_layout)
        layout.verify()
        raw_rules = io.cson_read_merge(self._res_path("[01]*.cson"), check_keys=True)  # CSON rules glob pattern.
        rule_parser = RuleParser(raw_rules)
        board_defs = io.json_read(self._res_path("board_defs.json"))               # Board shape definitions.
        board_elems = io.cson_read(self._res_path("board_elems.cson"))             # Board elements definitions.
        return StenoEngineFactory(layout, rule_parser, board_defs, board_elems)

    def _res_path(self, filename:str) -> str:
        """ Return a full path to a built-in asset resource from a relative filename. """
        return os.path.join(self.resource_dir, filename)
