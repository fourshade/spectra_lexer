import sys

from .base import CORE
from .engine import Engine
from .group import ClassFilter, InstanceGroup


class Application(CORE):
    """ Abstract base application class for the Spectra program. The starting point for program logic. """

    def __init__(self):
        """ Build the components and assemble the engine with them, then store the component list for debugging. """
        components = self._build_components(self._class_paths())
        engine = self._build_engine(components, exc_command=CORE.HandleException)
        engine.connect(self)
        self.ALL_COMPONENTS = components
        # Load all resources and run the application.
        self.Load()
        self.run()

    def _class_paths(self) -> list:
        """ Return a list of modules or classes to draw components from. """
        raise NotImplementedError

    def _build_components(self, paths:list) -> InstanceGroup:
        """ Make and return a list of components from paths. """
        cmp_filter = ClassFilter(whitelist=CORE, blacklist=Application)
        return InstanceGroup(paths, cmp_filter)

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
