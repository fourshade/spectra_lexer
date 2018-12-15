from typing import Iterable

from spectra_lexer import SpectraComponent
from spectra_lexer.engine import SpectraEngine
from spectra_lexer.file import FileHandler
from spectra_lexer.lexer import StenoLexer
from spectra_lexer.search import SearchEngine


class SpectraApplication(SpectraComponent):
    """ Base class for operation of the Spectra program. Subclassed by GUI implementations. """

    engine: SpectraEngine = None  # Engine object. Must be accessible from subclasses.

    def __new__(cls, **kwargs):
        """ The component hierarchy must be completely put together before the engine is initialized.
            For that reason, all commands and components for applications are initialized in __new__. """
        self = super().__new__(cls)
        # Default non-GUI engine commands and components for basic operation of the program.
        self.add_commands({"set_status_message": print})
        self.add_children([FileHandler(), SearchEngine(), StenoLexer()])
        return self

    def __init__(self, rules_files:Iterable[str]=(), dict_files:Iterable[str]=None, **kwargs) -> None:
        """ Initialize the engine with this object as the root component.
            As the base class, unused keyword arguments are discarded.
            All components are immediately usable after engine creation. """
        super().__init__()
        self.engine = SpectraEngine(self)
        # If <rules_files> is given as a parameter, load the rules files inside it and send them to the lexer.
        # If the parameter is empty or not given, load the rules from the built-in directories.
        self.engine_call("file_load_rules", rules_files, "command line")
        # If <dict_files> is given as a parameter, try to load the steno dictionary files inside it on start-up.
        # If the parameter is given but empty, make an attempt to locate Plover's dictionaries and load those.
        # If the parameter is not given at all, do nothing. A subclass might provide the search dict.
        if dict_files is not None:
            self.engine_call("file_load_translations", dict_files, "command line")
