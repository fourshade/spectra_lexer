""" Base module for the core Spectra package. """

import argparse

from spectra_lexer import Application
from spectra_lexer.core.config import ConfigManager
from spectra_lexer.core.file import FileHandler
from spectra_lexer.core.lexer import StenoLexer
from spectra_lexer.core.rules import RulesManager
from spectra_lexer.core.translations import TranslationsManager


class CoreApplication(Application):
    """ Application to handle fundamental operations of the Spectra lexer with base components. """

    def __init__(self, *cls_iter:type):
        """ Component classes of the base application. """
        super().__init__(FileHandler,
                         ConfigManager,
                         RulesManager,
                         TranslationsManager,
                         StenoLexer, *cls_iter)

    def start(self, **opts) -> None:
        """ Send the start signal with options from command line arguments parsed from sys.argv,
            followed by keyword options given directly by subclasses or by main(). """
        # Suppress defaults for unused options so that they don't override the ones from subclasses with None.
        parser = argparse.ArgumentParser(argument_default=argparse.SUPPRESS)
        for c in opts:
            parser.add_argument('--' + c)
        # Command-line options must be added with update() to enforce precedence and eliminate duplicates.
        opts.update(vars(parser.parse_args()))
        self.call("start", **opts)
