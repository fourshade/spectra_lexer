from spectra_lexer.engine import SpectraEngine
from spectra_lexer.file import FileHandler
from spectra_lexer.lexer import StenoLexer
from spectra_lexer.search import SearchEngine


class SpectraApplication:
    """ Base class for operation of the Spectra program. Subclassed by GUI implementations. """

    engine: SpectraEngine = None  # Engine object. Must be accessible from subclasses.

    def __init__(self, *components, **kwargs) -> None:
        """ Add all components from subclasses and initialize the engine with the root components.
            Start the engine with all keyword arguments from command line. """
        self.engine = SpectraEngine(FileHandler(), SearchEngine(), StenoLexer(), *components, **kwargs)
