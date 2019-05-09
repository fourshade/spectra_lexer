from typing import Callable

from .component import ComponentGroup
from .runtime import Runtime


class Application:
    """ Base application class for the Spectra program. The starting point for program logic.
        Routes messages and data structures between all constituent components using an engine. """

    DESCRIPTION: str  # String shown in command-line help.

    call: Callable = None

    def __init__(self):
        """ Build the runtime and get a top-level callable. """
        runtime = self._runtime()
        components = ComponentGroup.from_paths(self._class_paths())
        self.call = runtime.setup(components)
        # Initialize all resources in order using the main engine.
        # The mod classes will have sorted any dependencies out.
        for k, arg in components.get_setup_commands():
            self.call(k, arg)

    def _class_paths(self) -> list:
        """ Return lists of modules or classes to draw components from, one per execution unit. """
        raise NotImplementedError

    def _runtime(self) -> Runtime:
        """ Make a new runtime; may differ for subclasses. """
        return Runtime()

    def run(self) -> int:
        """ After everything else is ready, a primary task may be run. It may return an exit code to main().
            A batch operation can run until complete, or a GUI event loop can run indefinitely. """
        raise NotImplementedError
