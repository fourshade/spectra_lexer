from typing import Callable, Dict, List


class SpectraComponent:
    """
    Base class for any component that sends and receives commands from the Spectra engine.
    It is the root class of the Spectra lexer object hierarchy, being subclassed directly
    or indirectly by nearly every important (externally-visible) piece of the program.
    As such, it cannot depend on anything inside the package itself.

    The super() method is unreliable with extended multiple-inheritance hierarchies. It is far
    too easy for one of the many ancestors of a class to break the super() call chain on the
    way to __init__ in this class, so it is skipped and attributes are checked dynamically.
    """

    def add_commands(self, cmd_dict:Dict[str, Callable]) -> None:
        """ Components may add commands they accept here, overwriting commands with the same name from superclasses. """
        self.CMD_DICT.update(cmd_dict)

    def add_children(self, subcomponents:List[__qualname__]) -> None:
        """ Components may add child components (with lifecycles shorter than or equal to their own) here. """
        self.SUBCOMPONENTS.extend(subcomponents)

    def set_engine_callback(self, cb:Callable=lambda *args: None) -> None:
        """ Set engine command callback. Default is a no-op (useful for testing individual components). """
        self.engine_call = cb

    def remove_engine_callback(self) -> None:
        """ Remove callback so that engine calls result in attribute exceptions again. """
        del self.engine_call

    @property
    def CMD_DICT(self) -> Dict[str, Callable]:
        """ Dict of engine commands. Format is {"command": callback}. """
        if not hasattr(self, "_CMD_DICT"):
            self._CMD_DICT = {}
        return self._CMD_DICT

    @property
    def SUBCOMPONENTS(self) -> List[__qualname__]:
        """ List of child components to be added recursively to the engine. """
        if not hasattr(self, "_SUBCOMPONENTS"):
            self._SUBCOMPONENTS = []
        return self._SUBCOMPONENTS
