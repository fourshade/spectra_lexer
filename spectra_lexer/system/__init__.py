""" Package for the system components of Spectra. These handle operations required for the most basic functionality. """

from .cmdline import CmdlineParser
from .config import ConfigManager
from .console import ConsoleManager
from .parallel import ParallelExecutor

from .app import ConsoleApplication
