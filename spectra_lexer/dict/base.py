from spectra_lexer import Composite
from spectra_lexer.dict.config import ConfigManager
from spectra_lexer.dict.rules import RulesManager
from spectra_lexer.dict.translations import TranslationsManager


class DictManager(Composite):
    """ Handles all conversion and merging required for file operations on specific types of dicts. """

    ROLE = "dict"
    COMPONENTS = [ConfigManager, RulesManager, TranslationsManager]
