import argparse
import sys
import traceback

from spectra_lexer import Component
from spectra_lexer.dict import DictManager
from spectra_lexer.engine import SpectraEngine
from spectra_lexer.file import FileHandler
from spectra_lexer.lexer import StenoLexer
from spectra_lexer.search import SearchEngine
from spectra_lexer.text import CascadedTextFormatter

# Constituent components of the base application. These should be enough to run the lexer in batch mode.
BASE_COMPONENTS = [("file",   FileHandler),
                   ("dict",   DictManager),
                   ("search", SearchEngine),
                   ("lexer",  StenoLexer),
                   ("text",   CascadedTextFormatter)]


class SpectraApplication:
    """ Base class for fundamental operations of the Spectra lexer. """

    engine: SpectraEngine  # Engine must be accessible to subclasses.

    def __init__(self, *components:Component):
        """ Create all necessary base components and combine them with those from subclasses. """
        base_components = [tp() for (k, tp) in BASE_COMPONENTS]
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
            by main(), and send the start signal. Load the initial rule set after everything else is configured. """
        opts.update(self.parse_args(*cmd_args))
        self.engine.call("start", **opts)
        self.engine.call("dict_load_rules")

    def parse_args(self, *cmd_args:str) -> dict:
        """ Parse command-line arguments into a dict for the application and components. """
        # For the base application, specific config files may be used.
        parser = argparse.ArgumentParser(description='Run the Spectra Steno Lexer.')
        parser.add_argument('--cfg')
        return vars(parser.parse_args(cmd_args))
