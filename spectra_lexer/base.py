""" Base module of the Spectra lexer package. Contains the most fundamental components. Don't touch anything... """

from typing import ClassVar, Hashable, Iterable, List, NamedTuple, Tuple

from spectra_lexer.utils import nop


class CommandActions(NamedTuple):
    """ Contains actions that constitute a command, including a function call and/or a subsequent command. """
    func: callable      # Function or bound method to call.
    dispatch: callable  # Function with instructions on which command to execute next, if any.


class Component:
    """
    Base class for any component that sends and receives commands from the Spectra engine.
    It is the root class of the Spectra lexer object hierarchy, being subclassed directly
    or indirectly by nearly every important (externally-visible) piece of the program.
    As such, it cannot depend on anything inside the package itself except pure utility functions.
    """

    _cmd_attr_list: ClassVar[List[tuple]] = []  # Default class command parameter list; meant to be copied.
    engine_call: callable = nop  # Default engine callback is a no-op (useful for testing individual components).

    def __init_subclass__(cls) -> None:
        """ Make a list of commands this component class handles with methods that handle each one.
            Each engine-callable method (callable class attribute) has its command info saved on attributes.
            Save each of these to a list. Combine it with the parent's command list to make a new child list.
            This new combined list covers the full inheritance tree. Parent commands execute first. """
        cmd_list = [(attr, *func.cmd) for attr, func in cls.__dict__.items()
                    if callable(func) and hasattr(func, "cmd")]
        cls._cmd_attr_list = cmd_list + cls._cmd_attr_list

    def commands(self) -> List[Tuple[Hashable, CommandActions]]:
        """ Bind all class command functions to the instance and return the raw commands. """
        return [(key, CommandActions(getattr(self, attr), dsp)) for attr, key, dsp in self._cmd_attr_list]

    def set_engine_callback(self, cb:callable=nop) -> None:
        """ Set the callback used for engine calls by individual components. """
        self.engine_call = cb


class Composite(Component):
    """ Component container; all commands and callbacks are routed to/from child components,
        but the engine can't tell the difference. May also contain its own commands. """

    _children: Iterable[Component] = ()

    def set_children(self, children:Iterable[Component]) -> None:
        self._children = list(children)

    def commands(self) -> list:
        cmds = super().commands()
        return cmds + [i for c in self._children for i in c.commands()]

    def set_engine_callback(self, *args) -> None:
        super().set_engine_callback(*args)
        for c in self._children:
            c.set_engine_callback(*args)
