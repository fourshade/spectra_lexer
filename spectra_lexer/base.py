""" Base module of the Spectra lexer core package. Contains the most fundamental components. Don't touch anything...
    There are no type hints here. No type checker would stand a chance against all the descriptor voodoo. """

from collections import defaultdict
from functools import partial

from spectra_lexer.utils import nop


class Command:
    """ Disposable descriptor for recording component class commands. """
    on = classmethod(partial)  # Decorator for engine command methods.
    def __init__(self, key, func, pipe_to=None, **kwargs):
        self.__dict__ = dict(locals())
    def __set_name__(self, owner, name):
        """ Add to the command dict, put the original function back, and chain the __set_name__ call if necessary. """
        owner.cmds[self.key] = name, self.pipe_to, self.kwargs
        setattr(owner, name, self.func)
        getattr(self.func, "__set_name__", nop)(owner, name)


class Resource:
    """ An external resource, configured before the application starts. """
    def __init__(self, src, key, default=None, desc=""):
        self.__dict__ = dict(locals())
    def __set_name__(self, owner, name):
        """ Add to the option dict, put the default value in its place, and make the command. """
        owner.RES[self.src].append(self)
        setattr(owner, name, self.default)
        cmdkey = f"set_{self.src}_{self.key}"
        Command.on(cmdkey)(partial(setattr, owner, name)).__set_name__(owner, cmdkey)


class ComponentMeta(type):
    """ Metaclass for all subclasses of Component. """
    RES = defaultdict(list)  # Dict of options from all classes combined into a list for each source.
    def __prepare__(name, bases, _cmd=Command, _res=Resource):
        """ Merge commands from all bases in order so that this class inherits from and overrides all of its parents.
            Add references to the command decorator and resource class for every component. """
        return {"cmds": {k: v for b in bases for k, v in b.cmds.items()}, "on": _cmd.on, "Resource": _res}


class Component(metaclass=ComponentMeta):
    """ Base class for any component that sends and receives commands from the Spectra engine.
        It is the root class of the Spectra lexer object hierarchy, being subclassed directly
        or indirectly by nearly every important (externally-visible) piece of the program.
        As such, it cannot depend on anything except pure utility functions. """
    engine_call = nop  # Default engine callback is a no-op (useful for testing individual components).
    def __getstate__(self):
        """ Each component has a reference to the engine through self.engine_call, which respectively has a reference
            to almost everything else. Without intervention, if the pickler tries to pickle a component, it will
            follow the reference and attempt to pickle the engine, which results in pickling the entire program.
            Some parts are unavoidably unpickleable, so the reference chain must be stopped by removing engine_call.
            Unfortunately, this means no engine calls may be made by components after unpickling. """
        return {**vars(self), "engine_call": nop}
