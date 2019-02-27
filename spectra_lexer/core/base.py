""" Base module for the core Spectra package. """

from spectra_lexer import Application
from spectra_lexer.core.config import ConfigManager
from spectra_lexer.core.file import FileHandler
from spectra_lexer.core.lexer import StenoLexer
from spectra_lexer.core.parallel import ParallelExecutor
from spectra_lexer.core.rules import RulesManager
from spectra_lexer.core.translations import TranslationsManager
from spectra_lexer.options import CommandOption


class CoreApplication(Application):
    """ Application to handle fundamental operations of the Spectra lexer with base components. """

    def __init__(self, *cls_iter:type):
        """ Component classes of the base application. """
        super().__init__(ParallelExecutor,
                         FileHandler,
                         ConfigManager,
                         RulesManager,
                         TranslationsManager,
                         StenoLexer, *cls_iter)

    def start(self, **opts) -> None:
        """ Parse command line arguments from sys.argv and keyword options given by subclasses or by main().
            Send the start signal with the keyword options from subclasses or main() only. """
        CommandOption.parse_args(**opts)
        self.call("start", **opts)
