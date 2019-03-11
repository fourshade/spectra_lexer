""" Base module of the Spectra lexer core package. Contains the most fundamental components. Don't touch anything... """

from functools import partial
from typing import Callable, NamedTuple, Iterable

from spectra_lexer.utils import merge, nop


class Option(NamedTuple):
    """ A customizable option. These are configured before the application actually starts. """
    src: str                # Designator for an option's source handling command.
    key: str                # Option key. Must be unique for a given source.
    default: object = None  # Externally visible default value.
    desc: str = ""          # Description as shown on documentation page.


def Command(key, *cmd_args, **cmd_kwargs) -> Callable:
    """ Decorator for component engine command flow. """
    def add_cmd_attr(func:Callable) -> Callable:
        """ Add a command trigger to a list on an attribute. """
        func.cmdx = getattr(func, "cmdx", []) + [(key, cmd_args, cmd_kwargs)]
        return func
    return add_cmd_attr


class ComponentMeta(type):
    """ Metaclass for all subclasses of Component. """

    def __prepare__(*args) -> dict:
        # Add references to the command decorator and option class for every component.
        return dict(on=Command, pipe=Command, Option=Option)

    def __new__(mcs, name:str, bases:tuple, dct:dict):
        """ Get every command and option defined on the class and sort them into dicts. """
        cmds = {key: (attr, params) for attr, obj in dct.items() if hasattr(obj, "cmdx") for key, *params in obj.cmdx}
        opts = {attr: obj for attr, obj in dct.items() if isinstance(obj, Option)}
        # After saving all options to a dict, overwrite them in the class with their default values.
        # Merge variables from all bases in order so that this class inherits from and overrides all of its parents.
        dct.update({attr: opt.default for attr, opt in opts.items()},
                   cmds=merge([*[b.cmds for b in bases], cmds]),
                   opts=merge([*[b.opts for b in bases], opts]))
        return super().__new__(mcs, name, bases, dct)


class Component(metaclass=ComponentMeta):
    """
    Base class for any component that sends and receives commands from the Spectra engine.
    It is the root class of the Spectra lexer object hierarchy, being subclassed directly
    or indirectly by nearly every important (externally-visible) piece of the program.
    As such, it cannot depend on anything except core helpers and pure utility functions.
    """

    engine_call: Callable = nop   # Default engine callback is a no-op (useful for testing individual components).

    def engine_connect(self, cb:Callable) -> None:
        """ Set the callback used for engine calls by this component. """
        self.engine_call = cb

    def engine_commands(self) -> Iterable[tuple]:
        """ Bind all class command functions to the instance and return a list of these to the engine.
            Make functions to set option attributes on the instance and add these as well. """
        return [(key, (getattr(self, attr), *params)) for key, (attr, params) in self.cmds.items()] + \
               [(f"set_{opt.src}_{opt.key}", (partial(setattr, self, attr), (), {})) for attr, opt in self.opts.items()]

    def engine_options(self) -> Iterable[Option]:
        """ Return all options (dict values) on this class to the engine. """
        return self.opts.values()
