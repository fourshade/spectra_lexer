""" Base package for GUI view controller layer. """

from .app import StenoConsoleApplication as console, StenoAnalyzeApplication as analyze, StenoIndexApplication as index
from .app import ViewApplication
from .base import VIEW
from .config import ConfigItem
from .view import ViewManager
