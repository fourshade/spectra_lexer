import sys
from traceback import print_exc

from .base import CORE
from .engine import Engine
from .group import InstanceGroup
from .main import main


class Application(CORE):
    """ Abstract base application class for the Spectra program. The starting point for program logic. """

    DESCRIPTION: str = "Spectra program."  # Program description as seen in the command line help.

    _components: InstanceGroup

    def __init__(self):
        """ Build the components and assemble the engine with them to get a top-level callable. """
        self._components = InstanceGroup(self._class_paths(), whitelist=CORE, blacklist=Application)
        self._engine(exc_command=CORE.HandleException).connect(self)

    def _class_paths(self) -> list:
        """ Return a list of modules or classes to draw components from. """
        raise NotImplementedError

    def _engine(self, **kwargs) -> Engine:
        """ Make and return a new engine; may differ for subclasses. """
        return Engine(self._components, **kwargs)

    def start(self) -> int:
        """ Start all auxiliary components and create a full component list for debugging. """
        self.ALL_COMPONENTS = list(self._components.recurse_items())
        self.Load()
        return self.run()

    def run(self) -> int:
        """ After everything else is ready, a primary task may be run. It may return an exit code to main().
            A batch operation can run until complete, or a GUI event loop can run indefinitely. """
        raise NotImplementedError

    def Exit(self) -> None:
        """ A worker thread calling sys.exit will not kill the main program, so it must be done here. """
        sys.exit()

    @classmethod
    def set_entry_point(cls, mode:str, **kwargs) -> None:
        """ Make an entry point for this application class and add it to the main dict. """
        main.add_entry_point(cls.app_main, mode, cls.DESCRIPTION, **kwargs)

    @classmethod
    def app_main(cls, *args, **kwargs) -> int:
        """ Create the application, run it, and return an exit code. Print uncaught exceptions before quitting. """
        try:
            return cls(*args, **kwargs).start()
        except Exception:
            print_exc()
            return -1
