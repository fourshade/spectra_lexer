import argparse

from spectra_lexer import Process
from spectra_lexer.config import ConfigManager
from spectra_lexer.file import FileHandler
from spectra_lexer.lexer import StenoLexer
from spectra_lexer.rules import RulesManager
from spectra_lexer.translations import TranslationsManager

# Constituent component classes of the base application. These should be enough to run the lexer in batch mode.
BASE_COMPONENTS = [FileHandler,
                   ConfigManager,
                   RulesManager,
                   TranslationsManager,
                   StenoLexer]


class SpectraApplication(Process):
    """ Process to handle fundamental operations of the Spectra lexer with base components. """

    ROLE = "app"

    def __init__(self, *cls_iter:type):
        """ Create all necessary components in order, starting from base components and moving to subclasses. """
        super().__init__(*BASE_COMPONENTS, *cls_iter)

    def start(self, **opts) -> None:
        """ Send the start signal with these options, in order of decreasing precedence:
            - Command line arguments parsed from sys.argv.
            - Keyword options given directly by subclasses or by main().
            - Fallback options to load the default config file and rule set.
            Keyword arguments must be combined in a dict in this order to enforce precedence. """
        all_opts = {"config": (), "rules": (), 'translations': None, **opts}
        # Suppress defaults for unused options so that they don't override the ones from subclasses with None.
        parser = argparse.ArgumentParser(argument_default=argparse.SUPPRESS)
        for c in all_opts:
            parser.add_argument('--' + c)
        all_opts.update(vars(parser.parse_args()))
        self.call("start", **all_opts)
