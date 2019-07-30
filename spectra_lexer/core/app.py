import sys

from .base import CORE
from .core import SpectraCore
from .cmdline import CmdlineOption
from .debug import DebugDict
from .engine import Engine


class Application(CORE):
    """ Abstract base application class for the Spectra program. The starting point for program logic. """

    def __init__(self):
        """ Build the components and assemble the engine with them, then store the component list for debugging. """
        components = self._build_components()
        engine = self._build_engine(components, exc_command=CORE.COREException)
        engine.connect(self)
        # Load all command line options and resources and run the application.
        CmdlineOption.process_all()
        debug_dict = DebugDict(components)
        self.COREDebug(debug_dict)
        self.Load()
        self.run()

    def _build_components(self) -> list:
        """ Make and return a list of components. """
        return [SpectraCore()]

    def _build_engine(self, components:list, **kwargs) -> Engine:
        """ Make and return a new engine; may differ for subclasses. """
        return Engine(components, **kwargs)

    def run(self) -> int:
        """ After everything else is ready, a primary task may be run. It may return an exit code to main().
            A batch operation can run until complete, or a GUI event loop can run indefinitely. """
        raise NotImplementedError

    def Exit(self) -> None:
        """ A worker thread calling sys.exit will not kill the main program, so it must be done here. """
        sys.exit()
