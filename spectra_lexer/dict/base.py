from spectra_lexer import Composite
from spectra_lexer.dict.config import ConfigManager
from spectra_lexer.dict.rules import RulesManager
from spectra_lexer.dict.translations import TranslationsManager

# Constituent components of the manager.
DICT_COMPONENTS = [ConfigManager, RulesManager, TranslationsManager]


class DictManager(Composite):
    """ Handles all conversion and merging required for file operations on specific types of dicts. """

    ROLE = "dict"

    def __init__(self):
        """ Assemble child components before the engine starts. """
        super().__init__()
        self.set_children([tp() for tp in DICT_COMPONENTS])
