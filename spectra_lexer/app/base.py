import sys
import traceback

from spectra_lexer import Component
from spectra_lexer.dict import DictManager
from spectra_lexer.engine import SpectraEngine
from spectra_lexer.file import FileHandler
from spectra_lexer.lexer import StenoLexer
from spectra_lexer.search import SearchEngine
from spectra_lexer.text import CascadedTextFormatter


class SpectraApplication:
    """ Base class for fundamental operations of the Spectra lexer involving keys, rules, and nodes. """

    engine: SpectraEngine  # Engine must be accessible to subclasses.

    def __init__(self, *components:Component):
        """ Initialize the engine and connect everything starting from the base components. """
        all_components = [FileHandler(), DictManager(), StenoLexer(),
                          SearchEngine(), CascadedTextFormatter(), *components]
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
        """ Send the bare command line options to the configuration module, then to all other components.
            Configure each loaded module, then send the start signal to finish setting up.
            Load the initial rule set after everything else is configured. """
        opts.update(_parse_args(*cmd_args))
        self.engine.call("start", **opts)
        self.engine.call("file_load_builtin_rules")


def _parse_args(*cmd_args:str) -> dict:
    """ Parse command-line arguments into a dict for the config manager and components.
        If the CFG option is given in the command line, it is the CFG file to load. """
    opt_dict = {}
    for arg in cmd_args:
        if arg.startswith("-cfg="):
            opt_dict["cfg"] = arg[5:]
    return opt_dict
