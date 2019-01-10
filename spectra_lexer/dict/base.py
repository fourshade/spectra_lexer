from spectra_lexer import Composite
from spectra_lexer.dict.config import ConfigManager
from spectra_lexer.dict.rules import RulesManager
from spectra_lexer.dict.translations import TranslationsManager

# Constituent components of the manager.
_COMPONENTS = [ConfigManager, RulesManager, TranslationsManager]


class DictManager(Composite):
    """ Handles all conversion and merging required for file operations on specific types of dicts. """

    def __init__(self):
        """ Assemble child components before the engine starts. """
        self.set_children([tp() for tp in _COMPONENTS])
