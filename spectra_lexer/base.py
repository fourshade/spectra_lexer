""" Base module of the Spectra lexer core package. Contains the most fundamental components. Don't touch anything... """

from typing import Callable, ClassVar, Dict, Hashable, List, Tuple

from spectra_lexer.utils import nop


def pipe(key:Hashable, next_key:Hashable=None, **cmd_kwargs) -> Callable:
    """ Decorator for component engine command flow. """
    def base_decorator(func:Callable) -> Callable:
        """ Call the command and pipe its return value to another command. """
        func.cmd = (key, next_key, cmd_kwargs)
        return func
    return base_decorator


# All command decorators currently do the same thing.
on = respond_to = fork = pipe


class Component:
    """
    Base class for any component that sends and receives commands from the Spectra engine.
    It is the root class of the Spectra lexer object hierarchy, being subclassed directly
    or indirectly by nearly every important (externally-visible) piece of the program.
    As such, it cannot depend on anything except core helpers and pure utility functions.
    """

    # Standard identifier for a component's function, usable in many ways (e.g. config page title).
    ROLE: ClassVar[str] = "UNDEFINED"

    _cmd_attr_dict: ClassVar[Dict[str, tuple]] = {}  # Default class command parameter dict; meant to be copied.
    engine_call: Callable = nop  # Default engine callback is a no-op (useful for testing individual components).

    def __init_subclass__(cls) -> None:
        """ Each engine-callable method is a class attribute with command info saved on it.
            Save each of these to a dict. Combine it with the parent's command dict to make a new child dict.
            This new combined dict covers the full inheritance tree. If a child command is different, it overrides. """
        cmd_dict = {attr: func.cmd for attr, func in vars(cls).items() if hasattr(func, "cmd")}
        cls._cmd_attr_dict = {**cmd_dict, **cls._cmd_attr_dict}

    def engine_connect(self, cb:Callable) -> None:
        """ Set the callback used for engine calls by this component. """
        self.engine_call = cb

    def engine_commands(self) -> List[Tuple[Hashable, tuple]]:
        """ Bind all class command functions to the instance and return the raw (key, (func, ...)) command tuples.
            Each command has a main callable followed by optional instructions on what to execute next. """
        return [(key, (getattr(self, attr), *params)) for (attr, (key, *params)) in self._cmd_attr_dict.items()]
