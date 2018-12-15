from functools import partial
from typing import Callable


class SpectraComponent:
    """ Base class for any component that sends and receives commands from the Spectra engine.
        It is the lowest-level class of the Spectra lexer package, being subclassed directly
        or indirectly by nearly every important (externally-visible) piece of the program.
        As such, it cannot depend on anything inside the package itself. """

    _test_callback: Callable = None     # External callback used to test-run components without the engine.

    def engine_commands(self) -> dict:
        """ Components provide a dict with the commands they accept here. By default, they accept nothing.
            Each subclass should add the commands from its super call to the ones it returns. """
        return {}

    def engine_subcomponents(self) -> tuple:
        """ Components provide a tuple of subcomponents to connect here. By default, they have none.
            Each subclass should add the components from its super call to the ones it returns. """
        return ()

    def __getattr__(self, attr:Callable) -> Callable:
        """ Any invoked method that isn't listed here is assumed to be an engine call.
            Commands called by an (unintentionally) unconnected component raise an error.
            In test mode, return the callback pre-loaded with the name of the method we tried to call. """
        if self._test_callback is not None:
            return partial(self._test_callback, attr)
        raise AttributeError("Engine call by unconnected component.")

    def set_test_callback(self, cb:Callable=lambda *args, **kwargs: None) -> None:
        """ In order to test individual components, set an external callback (that does nothing by default). """
        self._test_callback = cb
