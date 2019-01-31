""" Base module of the Spectra lexer package. Contains the most fundamental components. Don't touch anything... """

from typing import ClassVar, Iterable, List

from spectra_lexer.utils import nop


class Component:
    """
    Base class for any component that sends and receives commands from the Spectra engine.
    It is the root class of the Spectra lexer object hierarchy, being subclassed directly
    or indirectly by nearly every important (externally-visible) piece of the program.
    As such, it cannot depend on anything inside the package itself except pure utility functions.
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
        cmd_list = [(attr, func.cmd) for attr, func in cls.__dict__.items() if hasattr(func, "cmd")]
        cls._cmd_attr_list = cmd_list + cls._cmd_attr_list

    def engine_connect(self, cb:callable=nop) -> List[tuple]:
        """ Set the callback used for engine calls by this component.
            Bind all class command functions to the instance and return the raw (key, func, dispatch) command tuples.
            Each command has a main callable followed by one with instructions on what to execute next. """
        self.engine_call = cb
        return [(key, (getattr(self, attr), dispatch)) for (attr, (key, dispatch)) in self._cmd_attr_list]


class Composite(Component):
    """ Component container; all commands and callbacks are routed to/from child components,
        but the engine can't tell the difference. May also contain its own commands. """

    COMPONENTS: ClassVar[Iterable[type]] = ()  # Constructors for each child component.

    _children: List[Component]  # Finished child components.

    def __init__(self, args_iter:Iterable=iter(tuple, ...)):
        """ Assemble all listed child components before the engine starts.
            <args_iter> contains positional arguments for each constructor in order, defaulting to empty. """
        super().__init__()
        self._children = [tp(*args) for (tp, args) in zip(self.COMPONENTS, args_iter)]

    def engine_connect(self, *args) -> List[tuple]:
        cmds = super().engine_connect(*args)
        return cmds + [i for c in self._children for i in c.engine_connect(*args)]
