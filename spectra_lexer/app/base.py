import argparse

from spectra_lexer import Process
from spectra_lexer.dict import ConfigManager, RulesManager, TranslationsManager
from spectra_lexer.file import FileHandler
from spectra_lexer.lexer import StenoLexer
from spectra_lexer.search import SearchEngine

# Constituent component classes of the base application. These should be enough to run the lexer in batch mode.
BASE_COMPONENTS = [FileHandler,
                   ConfigManager,
                   RulesManager,
                   TranslationsManager,
                   SearchEngine,
                   StenoLexer]


class SpectraApplication(Process):
    """ Process to handle fundamental operations of the Spectra lexer with base components. """

    ROLE = "app"

    def __init__(self, *cls_iter:type):
        """ Create all necessary components in order, starting from base components and moving to subclasses. """
        super().__init__(*BASE_COMPONENTS, *cls_iter)

    def start(self, **opts) -> None:
        """ Send the start signal with these options, in order of decreasing precedence:
            - Options parsed from command line arguments.
            - Keyword options given directly by subclasses or by main().
            - Fallback options to load the default config file and rule set.
            Keyword arguments must be combined in a dict in this order to enforce precedence. """
        all_opts = {"config": (), "rules": (), **opts, **_parse_cmd_args()}
        super().start(**all_opts)


def _parse_cmd_args() -> dict:
    """ Parse command-line arguments from sys.argv into a dict for the application and components.
        Suppress defaults for unused options so that components can provide defaults themselves in start(). """
    parser = argparse.ArgumentParser(argument_default=argparse.SUPPRESS)
    # For the base application, specific files (one of each) may be loaded at start.
    parser.add_argument('--board')
    parser.add_argument('--config')
    parser.add_argument('--rules')
    parser.add_argument('--translations')
    return vars(parser.parse_args())
