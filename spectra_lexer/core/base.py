""" Base module for the core Spectra package. """

from spectra_lexer import Composite
from spectra_lexer.core.config import ConfigManager
from spectra_lexer.core.file import FileHandler
from spectra_lexer.core.lexer import StenoLexer
from spectra_lexer.core.rules import RulesManager
from spectra_lexer.core.translations import TranslationsManager


class Core(Composite):
    """ Central constructor/container for all components that provide basic application functionality. """

    ROLE = "core"

    def __init__(self):
        """ Component classes of the base application. These should be enough to run the lexer in batch mode. """
        super().__init__(FileHandler,
                         ConfigManager,
                         RulesManager,
                         TranslationsManager,
                         StenoLexer)
