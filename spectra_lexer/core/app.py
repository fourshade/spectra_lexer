from typing import Callable, Iterable

from .runtime import Runtime


class Application:
    """ Base application class for the Spectra program. The starting point for program logic. """

    DESCRIPTION: str = "Subclasses state their purpose here."
    CLASS_PATHS: Iterable = ()

    call: Callable = None

    def _new_runtime(self) -> Runtime:
        """ Make a new runtime from class paths given by the subclass. """
        return Runtime(self.CLASS_PATHS)

    def start(self, *args) -> None:
        """ Build the runtime, get a top-level callable, and start the app. """
        runtime = self._new_runtime()
        self.call = runtime.setup()
        return self.run(*args)

    def run(self, *args):
        """ After everything else is ready, a primary task may be run. It may return a single value to main().
            A batch operation can run until complete, or a GUI event loop can run indefinitely. """
        raise NotImplementedError
