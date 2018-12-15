from typing import Iterable

from spectra_lexer import SpectraComponent
from spectra_lexer.engine import SpectraEngine
from spectra_lexer.file import FileHandler
from spectra_lexer.lexer import StenoLexer
from spectra_lexer.search import SearchEngine


class SpectraApplication(SpectraComponent):
    """ Base class for operation of the Spectra program. Subclassed by GUI implementations. """

    engine: SpectraEngine = None  # Engine object. Must be accessible from subclasses.

    def __init__(self, files:Iterable[str]=None, **kwargs) -> None:
        """ Initialize the application with itself as the root component.
            As the base class, unused keyword arguments are discarded. """
        self.engine = SpectraEngine(self)
        # Load the rules dicts from the built-in directories.
        self.engine_send("file_load_rules_dicts")
        # If <files> was given as a parameter, try to load the steno dictionary files inside it on start-up.
        # If the parameter was given but empty, make an attempt to locate Plover's dictionaries and load those.
        # If the parameter is not given at all, do nothing. A subclass might provide the dicts.
        if files is not None:
            self.engine_send("file_load_steno_dicts", files)
            src_string = "command line" if files else "Plover config"
            self.engine_send("set_status_message", "Loaded dictionaries from {}.".format(src_string))

    def engine_subcomponents(self) -> tuple:
        """ Default non-GUI engine components for basic operation of the program. """
        return (*super().engine_subcomponents(), FileHandler(), SearchEngine(), StenoLexer())
