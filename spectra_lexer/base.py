from typing import Callable, Iterator, List, Tuple

from spectra_lexer.utils import nop, recurse


def on(command:str):
    """ Decorator for methods which handle engine commands. Only works with user-defined methods. """
    def on_decorator(func:Callable):
        func.cmd_str = command
        return func
    return on_decorator


class SpectraComponent:
    """
    Base class for any component that sends and receives commands from the Spectra engine.
    It is the root class of the Spectra lexer object hierarchy, being subclassed directly
    or indirectly by nearly every important (externally-visible) piece of the program.
    As such, it cannot depend on anything inside the package itself.

    The super() method is unreliable with extended multiple-inheritance hierarchies. It is far
    too easy for one of the many ancestors of a class (some of which may be from external libraries)
    to break the super() call chain on the way to __init__ in this class. For this reason,
    initialization is skipped and instance attributes are checked dynamically as properties.
    """

    def add_children(self, subcomponents:List[__qualname__]) -> None:
        """ Components may add child components (with lifecycles shorter than or equal to their own) here. """
        self.children.extend(subcomponents)

    def set_engine_callback(self, cb:Callable=nop) -> None:
        """ Set engine command callback. Default is a no-op (useful for testing individual components). """
        for c in recurse(self, iter_attr="children"):
            c.engine_call = cb

    def commands(self) -> Iterator[Tuple[str, Callable]]:
        """ Yield engine commands this component handles with the bound methods that handle each one. """
        for c in recurse(self, iter_attr="children"):
            cls = c.__class__
            cls_attrs = cls.__dict__.values()
            cls_methods = filter(callable, cls_attrs)
            command_methods = [meth for meth in cls_methods if hasattr(meth, "cmd_str")]
            for meth in command_methods:
                yield (meth.cmd_str, meth.__get__(c, cls))

    @property
    def children(self) -> List[__qualname__]:
        """ List of child components to be added recursively to the engine. """
        if not hasattr(self, "_SUBCOMPONENTS"):
            self._SUBCOMPONENTS = []
        return self._SUBCOMPONENTS
