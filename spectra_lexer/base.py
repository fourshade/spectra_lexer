""" Base module of the Spectra lexer core package. Contains the most fundamental components. Don't touch anything... """

from typing import Callable, ClassVar, List

from spectra_lexer.utils import nop


class ComponentMeta(type):

    def __prepare__(cls, bases, **kwargs) -> dict:
        # Combine all parent command lists to make a new child list.
        cmd_list = [cmd for b in bases for cmd in getattr(b, "_cmd_list", [])]
        def command(key:str, next_key:str=None, **cmd_kwargs) -> Callable:
            """ Decorator for component engine command flow. """
            def add_cmd_attr(func:Callable) -> Callable:
                """ Add a command to call the function. """
                cmd_list.append((func, key, next_key, cmd_kwargs))
                return func
            return add_cmd_attr
        # Add references to the command decorators for every component. All of them currently do the same thing.
        return {"_cmd_list": cmd_list, "on": command, "respond_to": command, "fork": command, "pipe": command}


class Component(metaclass=ComponentMeta):
    """
    Base class for any component that sends and receives commands from the Spectra engine.
    It is the root class of the Spectra lexer object hierarchy, being subclassed directly
    or indirectly by nearly every important (externally-visible) piece of the program.
    As such, it cannot depend on anything except core helpers and pure utility functions.
    """

    ROLE: ClassVar[str] = "UNDEFINED"  # Standard identifier for a component's function. Only one of each is allowed.

    _cmd_list: ClassVar[List[tuple]]  # Class command parameter list; meant to be copied by subclasses.
    engine_call: Callable = nop  # Default engine callback is a no-op (useful for testing individual components).

    def engine_connect(self, cb:Callable) -> None:
        """ Set the callback used for engine calls by this component. """
        self.engine_call = cb

    def engine_commands(self) -> List[tuple]:
        """ Return the unmodified command tuples. """
        return self._cmd_list
