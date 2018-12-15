from functools import partial
from typing import Iterable, Dict

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
        # Load the rules from the built-in directories and send them to the lexer.
        rules = self.engine_call("file_load_rules")
        self.engine_call("lexer_set_rules", rules)
        # If <files> was given as a parameter, try to load the steno dictionary files inside it on start-up.
        # If the parameter was given but empty, make an attempt to locate Plover's dictionaries and load those.
        # If the parameter is not given at all, do nothing. A subclass might provide the search dict.
        if files is not None:
            src_string = "command line" if files else "Plover config"
            self.load_translations_from(files, src_string)

    def engine_commands(self) -> dict:
        """ Individual components must define the signals they respond to and the appropriate callbacks. """
        return {**super().engine_commands(),
                "set_status_message": print}

    def engine_subcomponents(self) -> tuple:
        """ Default non-GUI engine components for basic operation of the program. """
        return (*super().engine_subcomponents(), FileHandler(), SearchEngine(), StenoLexer())

    def load_translations_from(self, files:Iterable[str], src_string:str=None) -> None:
        self.engine_call_async("file_load_translations", files,
                               callback=partial(self._on_translations_loaded, src_string=src_string))

    def _on_translations_loaded(self, search_dict:Dict[str, str], src_string:str=None):
        """ When we get the prepared dict from the file handler, give it to the search engine and show a message. """
        self.engine_call("search_set_dict", search_dict)
        if src_string is not None:
            self.engine_call("set_status_message", "Loaded dictionaries from {}.".format(src_string))
