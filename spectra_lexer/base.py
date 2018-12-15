from typing import Callable, Optional


class SpectraComponent:
    """ Base class for any component that sends and receives commands from the Spectra engine.
        It is the lowest-level class of the Spectra lexer package, being subclassed directly
        or indirectly by nearly every important (externally-visible) piece of the program.
        As such, it cannot depend on anything inside the package itself. """

    def engine_send(self, command:str, *args) -> Exception:
        """ Any command that gets called by an (unintentionally) unconnected component raises an error. """
        raise AttributeError("Signal sent by unconnected component.")

    def engine_commands(self) -> dict:
        """ Components provide a dict with the commands they accept here. By default, they accept nothing. """
        return {}

    def engine_subcomponents(self) -> tuple:
        """ Components provide a tuple of subcomponents to connect here. By default, they have none. """
        return ()

    def set_engine_callback(self, callback:Optional[Callable]=None) -> None:
        """ Override the engine_send method to start sending commands to the engine via <callback>.
            If <callback> is None, run the component without the engine by setting engine_send to do nothing. """
        if callback is None:
            self.engine_send = lambda *args: None
        else:
            self.engine_send = callback

    def remove_engine_callback(self) -> None:
        """ Remove the engine_send instance method so it throws an exception again. """
        del self.engine_send
