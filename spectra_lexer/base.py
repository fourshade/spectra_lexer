""" Base module of the Spectra lexer core package. Contains the most fundamental components. Don't touch anything... """

from functools import partial
from typing import ClassVar, Hashable, Iterable, List

from spectra_lexer.engine import Engine
from spectra_lexer.utils import nop


def pipe(key:Hashable, next_key:Hashable=None, **cmd_kwargs) -> callable:
    """ Decorator for component engine command flow. """
    def base_decorator(func:callable) -> callable:
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

    # Standard identifier for a component's function, usable in many ways (i.e. # config page).
    ROLE: ClassVar[str] = "UNDEFINED"

    _cmd_attr_list: ClassVar[List[tuple]] = []  # Default class command parameter list; meant to be copied.
    engine_call: callable = nop  # Default engine callback is a no-op (useful for testing individual components).

    def __init_subclass__(cls) -> None:
        """ Make a list of commands this component class handles with methods that handle each one.
            Each engine-callable method (class attribute) has its command info saved on attributes.
            Save each of these to a list. Combine it with the parent's command list to make a new child list.
            This new combined list covers the full inheritance tree. Parent commands execute first. """
        cmd_list = [(attr, *func.cmd) for attr, func in vars(cls).items() if hasattr(func, "cmd")]
        cls._cmd_attr_list = cmd_list + cls._cmd_attr_list

    def engine_connect(self, cb:callable) -> None:
        """ Set the callback used for engine calls by this component. """
        self.engine_call = cb

    def engine_commands(self) -> List[tuple]:
        """ Bind all class command functions to the instance and return the raw (key, (func, ...)) command tuples.
            Each command has a main callable followed by optional instructions on what to execute next. """
        return [(key, (getattr(self, attr), *args)) for (attr, key, *args) in self._cmd_attr_list]


class Composite(Component):

    components: List[Component]  # List of all child components. Should not change after initialization.

    def __init__(self, *cls_iter:type, args_iter:Iterable=iter(tuple, ...)):
        """ Assemble child components from constructors.
            <args_iter> contains positional arguments for each constructor in order, defaulting to empty. """
        self.components = [cls(*args) for (cls, args) in zip(cls_iter, args_iter)]

    def engine_connect(self, cb:callable) -> None:
        for c in self.components:
            c.engine_call = cb

    def engine_commands(self) -> List[tuple]:
        return [cmd for c in self.components for cmd in c.engine_commands()]


class Process(Engine):
    """ Runnable component setup for an engine. """

    components: List[Component]  # List of all connected components. Should not change after initialization.

    def __init__(self, *cls_iter:type, args_iter:Iterable=iter(tuple, ...)):
        """ Assemble child components from constructors and initialize the engine.
            <args_iter> contains positional arguments for each constructor in order, defaulting to empty. """
        super().__init__()
        self.components = [cls(*args) for (cls, args) in zip(cls_iter, args_iter)]
        # Add (key, (func, ...)) command tuples and set callbacks for all child components.
        for c in self.components:
            for (key, cmd) in c.engine_commands():
                self.setdefault(key, []).append(cmd)
            c.engine_connect(self.call)


class Subprocess(Process, Component):
    """ Runnable component setup that acts as a component itself to a parent engine. """

    def engine_commands(self) -> List[tuple]:
        """ Any command using a key serviced by a child component should be forwarded here by the parent engine. """
        return [(key, (partial(self.call, key), None, {})) for key in self]

    def __missing__(self, key:Hashable) -> list:
        """ Any command we can't find is forwarded to the parent engine. """
        return [(partial(self.engine_call, key), None, {})]
