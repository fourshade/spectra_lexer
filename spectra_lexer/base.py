from typing import Callable, Dict, List, Tuple


class SpectraComponent:
    """
    Base class for any component that sends and receives commands from the Spectra engine.
    It is the root class of the Spectra lexer object hierarchy, being subclassed directly
    or indirectly by nearly every important (externally-visible) piece of the program.
    As such, it cannot depend on anything inside the package itself.

    The super() method is unreliable with extended multiple-inheritance hierarchies. It is far
    too easy for one of the many ancestors of a class (some of which may be from external libraries)
    to break the super() call chain on the way to __init__ in this class. For this reason,
    initialization is skipped and instance attributes are checked dynamically as properties. """

    def add_children(self, subcomponents:List[__qualname__]) -> None:
        """ Components may add child components (with lifecycles shorter than or equal to their own) here. """
        self.SUBCOMPONENTS.extend(subcomponents)

    def set_engine_callback(self, cb:Callable=lambda *args: None) -> None:
        """ Set engine command callback. Default is a no-op (useful for testing individual components). """
        self.engine_call = cb
        for c in self.SUBCOMPONENTS:
            c.set_engine_callback(cb)

    def command_list(self) -> List[Tuple[str, Callable]]:
        """ Return a list of engine commands this component handles with the bound methods that handle each one. """
        cls = self.__class__
        cls_attrs = cls.__dict__.values()
        cls_methods = filter(callable, cls_attrs)
        command_methods = [meth for meth in cls_methods if hasattr(meth, "cmd_str")]
        cmd_list = [(meth.cmd_str, meth.__get__(self, cls)) for meth in command_methods]
        for c in self.SUBCOMPONENTS:
            cmd_list += c.command_list()
        return cmd_list

    @property
    def SUBCOMPONENTS(self) -> List[__qualname__]:
        """ List of child components to be added recursively to the engine. """
        if not hasattr(self, "_SUBCOMPONENTS"):
            self._SUBCOMPONENTS = []
        return self._SUBCOMPONENTS


def on(command:str):
    """ Decorator for methods which handle engine commands. Only works with user-defined methods. """
    def on_decorator(func:Callable):
        func.cmd_str = command
        return func
    return on_decorator
