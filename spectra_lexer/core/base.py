""" Base module of the Spectra lexer core package. Contains the most fundamental components. Don't touch anything... """

from typing import ClassVar, Hashable, Iterable, List

from spectra_lexer.core.engine import SpectraEngine
from spectra_lexer.utils import nop


def pipe(cmd_key:Hashable, next_key:Hashable=None, **cmd_kwargs) -> callable:
    """ Decorator for component engine command flow. """
    def base_decorator(func:callable) -> callable:
        """ Call the command and pipe its return value to another command. """
        func.cmd = (cmd_key, next_key, cmd_kwargs)
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
        cmd_list = [(attr, *func.cmd) for attr, func in cls.__dict__.items() if hasattr(func, "cmd")]
        cls._cmd_attr_list = cmd_list + cls._cmd_attr_list

    def engine_connect(self, cb:callable) -> None:
        """ Set the callback used for engine calls by this component. """
        self.engine_call = cb

    def engine_commands(self) -> List[tuple]:
        """ Bind all class command functions to the instance and return the raw (key, (func, ...)) command tuples.
            Each command has a main callable followed by optional instructions on what to execute next. """
        return [(key, (getattr(self, attr), *args)) for (attr, key, *args) in self._cmd_attr_list]


class Composite(Component):
    """ Component container; all commands and callbacks are routed to/from child components. """

    components: List[Component]  # List of all connected components. Should not change after initialization.

    def __init__(self, *cls_iter:type, args_iter:Iterable=iter(tuple, ...)):
        """ Assemble all listed child components before the engine starts.
            <args_iter> contains positional arguments for each constructor in order, defaulting to empty. """
        super().__init__()
        self.components = [cls(*args) for (cls, args) in zip(cls_iter, args_iter)]

    def engine_connect(self, cb:callable) -> None:
        """ Set the callback used for engine calls by this component. """
        for c in self.components:
            c.engine_connect(cb)

    def engine_commands(self) -> List[tuple]:
        """ Return the raw (key, (func, dispatch)) command tuples. """
        return [i for c in self.components for i in c.engine_commands()]


class Process:
    """ Runnable component setup with an engine. """

    root: Composite
    engine: SpectraEngine  # Engine must be accessible to subclasses.

    def __init__(self, *cls_iter:type, args_iter:Iterable=iter(tuple, ...)):
        """ Assemble child components from constructors and initialize the engine. """
        self.root = Composite(*cls_iter, args_iter=args_iter)
        self.engine = SpectraEngine(self.root.engine_commands())
        self.root.engine_connect(self.engine.call)

    def start(self, **opts) -> None:
        """ Send the start signal with all options. """
        self.engine.call("start", **opts)
