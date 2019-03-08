""" Base module of the Spectra lexer core package. Contains the most fundamental components. Don't touch anything... """

from typing import Callable, ClassVar

from spectra_lexer.utils import nop


class Option:
    """ A customizable option. """

    src: str     # Role of an option's source handler component.
    key: str     # Option key. Must be unique for a given source.
    val: object  # Externally visible value, initialized to default.
    desc: str    # Description as shown on documentation page.
    tp: type     # Type of the default value, used for conversion.

    def __init__(self, src:str, key:str, default:object=None, desc:str=""):
        self.src = src
        self.key = key
        self.val = default
        self.desc = desc
        self.tp = type(default)

    def __get__(self, instance, owner) -> object:
        """ Options are accessed through the descriptor by the component itself. """
        return self.val

    def __set__(self, instance, value:object) -> None:
        """ Options typically come from strings, so they are converted to the most likely useful type. """
        if self.tp is None or value is None:
            self.val = value
        else:
            self.val = self.tp(value)

    def __set_name__(self, owner, name:str) -> None:
        """ Set an additional attribute on the owner class to update this option on command. """
        src = self.src
        key = self.key
        def set_arg(cmp:Component, v:object) -> None:
            """ Overwrite this option with the applicable argument. """
            setattr(cmp, name, v)
        owner.on(f"set_{src}_{key}")(set_arg)
        owner.opt_list.append((src, key, self))


class ComponentMeta(type):

    def __prepare__(cls, bases, **kwargs) -> dict:
        # Combine all parent command lists to make a new child list.
        cmd_list = [cmd for b in bases for cmd in getattr(b, "cmd_list", [])]
        def command(key:str, next_key:str=None, **cmd_kwargs) -> Callable:
            """ Decorator for component engine command flow. """
            def add_cmd_attr(func:Callable) -> Callable:
                """ Add a command to call the function. """
                cmd_list.append((func, key, next_key, cmd_kwargs))
                return func
            return add_cmd_attr
        # Add references to the command decorators for every component. All of them currently do the same thing.
        decorators = dict.fromkeys(("on", "pipe", "respond_to"), command)
        return {"cmd_list": cmd_list, "opt_list": [], **decorators, "Option": Option}


class Component(metaclass=ComponentMeta):
    """
    Base class for any component that sends and receives commands from the Spectra engine.
    It is the root class of the Spectra lexer object hierarchy, being subclassed directly
    or indirectly by nearly every important (externally-visible) piece of the program.
    As such, it cannot depend on anything except core helpers and pure utility functions.
    """

    ROLE: ClassVar[str] = "UNDEFINED"  # Standard identifier for a component's function. Only one of each is allowed.

    engine_call: Callable = nop  # Default engine callback is a no-op (useful for testing individual components).

    def engine_connect(self, cb:Callable) -> None:
        """ Set the callback used for engine calls by this component. """
        self.engine_call = cb
