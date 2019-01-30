import argparse
import sys
import traceback

from spectra_lexer.dict import DictManager
from spectra_lexer.engine import SpectraEngine
from spectra_lexer.file import FileHandler
from spectra_lexer.lexer import StenoLexer
from spectra_lexer.search import SearchEngine

# Constituent component classes of the base application. These should be enough to run the lexer in batch mode.
BASE_COMPONENTS = [FileHandler,
                   DictManager,
                   SearchEngine,
                   StenoLexer]


class SpectraApplication:
    """ Base class for fundamental operations of the Spectra lexer. """

    components: list       # List of all currently connected components, mainly for introspection.
    engine: SpectraEngine  # Engine must be accessible to subclasses.

    def __init__(self, *components:type):
        """ Create all necessary components in order, starting from base components and moving to subclasses. """
        all_components = [*BASE_COMPONENTS, *components]
        self.components = [cls() for cls in all_components]
        # Initialize the engine and connect everything to it. Connections are currently permanent.
        self.engine = SpectraEngine(on_exception=self.handle_exception)
        for c in self.components:
            self.engine.connect(c)

    def handle_exception(self, e:Exception) -> bool:
        """ The stack trace for unhandled exceptions are piped to every connected text display surface.
            To avoid crashing Plover, exceptions are suppressed (by returning True) after display. """
        tb_lines = traceback.TracebackException.from_exception(e).format()
        tb_text = "".join(tb_lines)
        sys.stderr.write(tb_text)
        self.engine.call("new_exception_text", tb_text)
        return True

    def start(self, *cmd_args:str, **main_opts) -> None:
        """ Send the start signal with these options in order of precedence:
            - Options parsed from command line arguments.
            - Keyword options given directly by main().
            - Options to load the default config file and rule set.
            Keyword arguments must be combined in a dict in this order to enforce precedence. """
        all_opts = {"config": (), "rules": (), **main_opts, **_parse_cmd_args()}
        self.engine.call("start", **all_opts)


def _parse_cmd_args() -> dict:
    """ Parse command-line arguments from sys.argv into a dict for the application and components.
        Suppress defaults for unused options so that components can provide defaults themselves in start(). """
    parser = argparse.ArgumentParser(argument_default=argparse.SUPPRESS)
    # For the base application, specific files (one of each) may be loaded at start.
    parser.add_argument('--config')
    parser.add_argument('--rules')
    parser.add_argument('--translations')
    return vars(parser.parse_args())
