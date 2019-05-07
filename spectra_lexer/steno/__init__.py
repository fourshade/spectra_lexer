""" Package for the steno components of Spectra. These handle operations related to steno rules and translations. """

from .system import SystemManager
from .translations import TranslationsManager
from .index import IndexManager
from .lexer import StenoLexer
from .analyzer import StenoAnalyzer
basic = type("basic", (), dict(globals()))  # Subset of components that do not involve user interaction.
from .board import BoardRenderer
from .graph import GraphRenderer
from .search import SearchEngine

from .app import StenoAnalyzeApplication, StenoIndexApplication
