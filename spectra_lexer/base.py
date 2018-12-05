from typing import Iterable, List, Type

from spectra_lexer.engine import SpectraEngine, SpectraEngineComponent
from spectra_lexer.file import FileHandler
from spectra_lexer.lexer import StenoLexer
from spectra_lexer.search import SearchEngine

# Default non-GUI engine components for basic operation of the program. Each must initialize with no arguments.
BASE_COMPONENTS:List[Type[SpectraEngineComponent]] = [FileHandler, SearchEngine, StenoLexer]


class SpectraApplication:
    """ Top-level class for operation of the Spectra program. Subclassed by GUI implementations. """

    engine: SpectraEngine = None  # Engine object. Must be accessible from subclasses.

    def __init__(self, *, files:Iterable[str]=None, **kwargs) -> None:
        """ Initialize the application with base components and keyword arguments from the caller. """
        self.engine = SpectraEngine(*[cmp() for cmp in BASE_COMPONENTS])
        # Load the rules dicts from the built-in directories.
        self.engine.send("file_load_rules_dicts")
        # If <files> was given as a parameter, try to load the steno dictionary files inside it on start-up.
        # If the parameter was given but empty, make an attempt to locate Plover's dictionaries and load those.
        # If the parameter is not given at all, do nothing. A subclass might provide the dicts.
        if files is not None:
            self.engine.send("file_load_steno_dicts", files)
            src_string = "command line" if files else "Plover config"
            self.engine.send("set_status_message", "Loaded dictionaries from {}.".format(src_string))
