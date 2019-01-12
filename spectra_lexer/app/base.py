import argparse
import sys
import traceback

from spectra_lexer import Component
from spectra_lexer.dict import DictManager
from spectra_lexer.engine import SpectraEngine
from spectra_lexer.file import FileHandler
from spectra_lexer.lexer import StenoLexer
from spectra_lexer.search import SearchEngine

# Constituent components of the base application. These should be enough to run the lexer in batch mode.
BASE_COMPONENTS = [FileHandler,
                   DictManager,
                   SearchEngine,
                   StenoLexer]


class SpectraApplication:
    """ Base class for fundamental operations of the Spectra lexer. """

    engine: SpectraEngine  # Engine must be accessible to subclasses.

    def __init__(self, *components:Component):
        """ Create all necessary base components and combine them with those from subclasses. """
        base_components = [tp() for tp in BASE_COMPONENTS]
        all_components = (*base_components, *components)
        # Initialize the engine and connect everything to it. Connections are currently permanent.
        self.engine = SpectraEngine(on_exception=self.handle_exception)
        for c in all_components:
            self.engine.connect(c)

    def handle_exception(self, e:Exception) -> bool:
        """ The stack trace for unhandled exceptions are piped to every connected text display surface.
            To avoid crashing Plover, exceptions are suppressed (by returning True) after display. """
        tb_lines = traceback.TracebackException.from_exception(e).format()
        tb_text = "".join(tb_lines)
        sys.stderr.write(tb_text)
        self.engine.call("new_output_text", tb_text)
        return True

    def start(self, *cmd_args:str, **opts) -> None:
        """ Parse the bare command line arguments into a dict of options, combine them with those given directly
            by main(), and send the start signal. Load the config file and initial rule set last. """
        opts.update(_parse_args(*cmd_args))
        self.engine.call("start", **opts)
        self.engine.call("dict_load_config")
        self.engine.call("dict_load_rules")


def _parse_args(*cmd_args:str) -> dict:
    """ Parse command-line arguments into a dict for the application and components.
        Suppress defaults for unused options so that components can provide defaults themselves in start(). """
    parser = argparse.ArgumentParser(argument_default=argparse.SUPPRESS)
    # For the base application, specific files (one of each) may be loaded at start.
    parser.add_argument('--config')
    parser.add_argument('--rules')
    parser.add_argument('--translations')
    return vars(parser.parse_args(cmd_args))
