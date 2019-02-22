""" Base module for the core Spectra package. """

from spectra_lexer import Application
from spectra_lexer.core.config import ConfigManager
from spectra_lexer.core.file import FileHandler
from spectra_lexer.core.lexer import StenoLexer
from spectra_lexer.core.rules import RulesManager
from spectra_lexer.core.translations import TranslationsManager


class CoreApplication(Application):
    """ Process to handle fundamental operations of the Spectra lexer with base components. """

    def __init__(self, *cls_iter:type):
        """ Component classes of the base application. These should be enough to run the lexer in batch mode. """
        super().__init__(FileHandler,
                         ConfigManager,
                         RulesManager,
                         TranslationsManager,
                         StenoLexer, *cls_iter)

    def start(self, **opts) -> None:
        """ Set fallback options to load the default config file and rule set. """
        all_opts = {"config": "", "rules": "", "translations": None, **opts}
        super().start(**all_opts)
