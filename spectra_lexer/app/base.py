import sys
import traceback

from spectra_lexer import SpectraComponent
from spectra_lexer.app.engine import SpectraEngine
from spectra_lexer.dict import DictManager
from spectra_lexer.file import FileHandler
from spectra_lexer.lexer import StenoLexer
from spectra_lexer.search import SearchEngine
from spectra_lexer.text import CascadedTextFormatter


class SpectraApplication:
    """ Base class for fundamental operations of the Spectra lexer involving keys, rules, and nodes. """

    def __init__(self, *components:SpectraComponent):
        """ Initialize the engine and connect everything starting from the base components. """
        all_components = [FileHandler(), DictManager(), StenoLexer(),
                          SearchEngine(), CascadedTextFormatter(), *components]
        self.engine = SpectraEngine(on_exception=self.handle_exception)
        for c in all_components:
            self.engine.connect(c)

    def start(self, **cfg_dict) -> None:
        """ Load the initial rule set. """
        self.engine.call("configure", **cfg_dict)
        self.engine.call("file_load_builtin_rules")

    def handle_exception(self, e:Exception) -> bool:
        """ The stack trace for unhandled exceptions are piped to every connected text display surface.
            To avoid crashing Plover, exceptions are suppressed (by returning True) after display. """
        tb_lines = traceback.TracebackException.from_exception(e).format()
        tb_text = "".join(tb_lines)
        sys.stderr.write(tb_text)
        self.engine.call("new_output_text", tb_text)
        return True
