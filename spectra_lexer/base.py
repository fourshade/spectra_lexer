""" Base module of the Spectra lexer core package. Contains the most fundamental components. Don't touch anything... """

from collections import namedtuple
from functools import partial


class Command(namedtuple("Command", "func key cmd_args cmd_kwargs", defaults=((), {}))):
    def __set_name__(self, owner, name:str) -> None:
        """ Add to the command dict, put the original function back, and chain the __set_name__ call if necessary. """
        func, key, *params = self
        owner.cmds[key] = name, params
        setattr(owner, name, func)
        if hasattr(func, "__set_name__"):
            func.__set_name__(owner, name)
    @classmethod
    def decorator(cls, key:str, *args, **kwargs):
        """ Decorator for component engine command flow. """
        return lambda func: cls(func, key, args, kwargs)


class Option(namedtuple("Option", "src key default desc", defaults=(None, ""))):
    """ A customizable option, configured before the application starts. """
    def __set_name__(self, owner, name:str) -> None:
        """ Add to the option dict, put the default value in its place, and make the command. """
        cmdkey = f"set_{self.src}_{self.key}"
        owner.opts[cmdkey] = self.src, self
        setattr(owner, name, self.default)
        Command(partial(setattr, owner, name), cmdkey).__set_name__(owner, cmdkey)


class ComponentMeta(type):
    """ Metaclass for all subclasses of Component. """
    def __prepare__(name:str, bases:tuple, _cmd=Command.decorator) -> dict:
        """ Merge commands from all bases in order so that this class inherits from and overrides all of its parents.
            Add references to the command decorator and option class for every component. """
        return {"cmds": {k: v for b in bases for k, v in b.cmds.items()}, "opts": {},
                "on": _cmd, "pipe": _cmd, "Option": Option}


class Component(metaclass=ComponentMeta):
    """ Base class for any component that sends and receives commands from the Spectra engine.
        It is the root class of the Spectra lexer object hierarchy, being subclassed directly
        or indirectly by nearly every important (externally-visible) piece of the program.
        As such, it cannot depend on anything except pure utility functions. """
    def engine_call(self, *args, **kwargs) -> None:
        """ Default engine callback is a no-op (useful for testing individual components). """
    def engine_connect(self, cb) -> None:
        """ Set the callback used for engine calls by this component. """
        self.engine_call = cb
    def engine_commands(self) -> list:
        """ Add the instance to each command and return a list to the engine. """
        return [(key, (self, attr, *params)) for key, (attr, params) in self.cmds.items()]
    def engine_options(self) -> list:
        """ Return all options (dict values) on this class to the engine. """
        return list(self.opts.values())
    def __getstate__(self) -> dict:
        """ Each component has a reference to the engine through self.engine_call, which respectively has a reference
            to almost everything else, Without intervention, if the pickler tries to pickle a component, it will
            follow the reference and attempt to pickle the engine, which results in pickling the entire program.
            Some parts are unavoidably unpickleable, so the reference chain must be stopped by removing engine_call.
            Unfortunately, this means no engine calls may be made by components after unpickling. """
        d = dict(vars(self))
        d.pop("engine_call", None)
        return d
