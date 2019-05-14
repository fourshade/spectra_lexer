from typing import Any, Callable, Hashable, List, Tuple

from .component import Option, Signal
from .engine import Engine
from .group import ComponentGroup


class COREApp:

    class Start:
        @Signal
        def on_app_start(self) -> None:
            """ Start operations such as batch tasks and resource loading. """
            raise NotImplementedError


class Application(COREApp):
    """ Abstract base application class for the Spectra program. The starting point for program logic. """

    DESCRIPTION: str = "Spectra program."  # Program description as seen in the command line help.
    CMDLINE_ARGS: list = []                # Subclasses may add extra args to the command line before parsing.

    call: Callable  # Top-level callable used to initialize and start the application.

    def __init__(self):
        """ Build the components and assemble the engine with them to get a top-level callable. """
        components = ComponentGroup(self._class_paths())
        self.call = self._engine(components)
        # Initialize all resources in order from the main engine. The mod classes will sort dependencies out.
        commands = [*self._global_commands(components), *Option.setup_commands(components)]
        for k, arg in commands:
            self.call(k, arg)

    def _class_paths(self) -> list:
        """ Return a list of modules or classes to draw components from.
            For multi-threaded applications, there may be a separate list for each thread. """
        raise NotImplementedError

    def _engine(self, components:ComponentGroup) -> Callable:
        """ Make and return a new engine callable; may differ for subclasses. """
        return Engine(components)

    def _global_commands(self, components:ComponentGroup) -> List[Tuple[Hashable, Any]]:
        """ List any necessary system resource commands that must be run before the components start. """
        return []

    def run(self) -> int:
        """ After everything else is ready, a primary task may be run. It may return an exit code to main().
            A batch operation can run until complete, or a GUI event loop can run indefinitely. """
        return self.call(self.Start)
