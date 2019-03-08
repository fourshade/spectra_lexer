""" Base module of the Spectra lexer core package. Contains the most fundamental components. Don't touch anything... """

from typing import Callable, NamedTuple

from spectra_lexer.utils import nop


class Option(NamedTuple):
    """ A customizable option. These are configured before the application actually starts. """
    src: str                # Designator for an option's source handling command.
    key: str                # Option key. Must be unique for a given source.
    default: object = None  # Externally visible default value.
    desc: str = ""          # Description as shown on documentation page.


class ComponentMeta(type):
    """ Metaclass for all subclasses of Component. Most assembly and configuration is done here,
        including handling of command decorators, config options, and command line arguments. """

    @classmethod
    def __prepare__(mcs, name:str, bases:tuple) -> dict:
        # Combine all parent command dicts to make a new child dict. Child commands will override these.
        cmd_dict = {key: cmd for b in bases for key, cmd in getattr(b, "cmd_dict", {}).items()}
        def command(key:str, next_key:str=None, **cmd_kwargs) -> Callable:
            """ Decorator for component engine command flow. """
            def add_cmd_attr(func:Callable) -> Callable:
                """ Add a command to call the function. """
                cmd_dict[key] = (func, next_key, cmd_kwargs)
                return func
            return add_cmd_attr
        # Add references to the command decorators for every component. All of them currently do the same thing.
        decorators = dict.fromkeys(("on", "pipe", "respond_to"), command)
        return {"cmd_dict": cmd_dict, **decorators, "Option": Option}

    def __init__(cls, name:str, bases:tuple, dct:dict):
        """ Get every option defined and set additional attributes to update each one on command. """
        super().__init__(name, bases, dct)
        cls.opt_list = []
        for attr, opt in dct.items():
            if isinstance(opt, Option):
                def set_arg(cmp:Component, v:object, attr=attr) -> None:
                    """ Overwrite this option value on the instance. """
                    setattr(cmp, attr, v)
                cmd = set_arg.__name__ = f"set_{opt.src}_{opt.key}"
                setattr(cls, cmd, cls.on(cmd)(set_arg))
                cls.opt_list.append((opt.src, opt))
                # Overwrite the option on the class with the default value.
                setattr(cls, attr, opt.default)


class Component(metaclass=ComponentMeta):
    """
    Base class for any component that sends and receives commands from the Spectra engine.
    It is the root class of the Spectra lexer object hierarchy, being subclassed directly
    or indirectly by nearly every important (externally-visible) piece of the program.
    As such, it cannot depend on anything except core helpers and pure utility functions.
    """

    engine_call: Callable = nop  # Default engine callback is a no-op (useful for testing individual components).

    def engine_connect(self, cb:Callable) -> None:
        """ Set the callback used for engine calls by this component. """
        self.engine_call = cb
