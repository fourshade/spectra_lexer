""" Base module of the Spectra lexer core package. Contains the most fundamental components. Don't touch anything...
    There are no type hints here. No type checker would stand a chance against all the descriptor voodoo. """

from collections import defaultdict
from functools import partial, partialmethod

from spectra_lexer.struct import struct
from spectra_lexer.utils import nop


class Marker(struct, _fields=["key"], value=None, _kwargs="kwargs"):
    """ Disposable descriptor for recording component data. """

    _DICT = {}  # Main data dict with component classes as keys and lists of marker keys/instances as values.

    def __init_subclass__(cls, **kwargs):
        """ Make a new data dict for each subclass. """
        super().__init_subclass__(**kwargs)
        cls._DICT = defaultdict(list)

    def __set_name__(self, owner, name):
        """ Add to the data dicts, put the original value back, and chain the __set_name__ call if necessary. """
        self._attr = name
        self._DICT[owner].append((self.key, self))
        v = self.value
        setattr(owner, name, v)
        getattr(v, "__set_name__", nop)(owner, name)

    @classmethod
    def get_all(cls, owner):
        """ Return each marker of this type from the owner class's hierarchy along with its key. """
        return [m for tp in owner.__mro__ for m in cls._DICT[tp]]


class Command(Marker, pipe_to=None):
    """ Descriptor for recording and executing component class commands. """
    on = classmethod(partial)  # Decorator for engine command methods.

    def __call__(self, *args, **kwargs):
        """ If there's a follow-up command and the output value wasn't None, run it. Return the original output. """
        value = self._func(*args, **kwargs)
        if value is not None and self.pipe_to is not None:
            # Normal tuples (not subclasses) will be automatically unpacked into the next command.
            next_args = value if type(value) is tuple else (value,)
            self._engine_call(self.pipe_to, *next_args, **self.kwargs)
        return value

    def bind(self, cmp, engine_cb):
        """ Bind a component instance to the command and return a final callable. """
        self._engine_call = engine_cb
        self._func = getattr(cmp, self._attr)
        return self


class Resource(Marker, desc="", deco=False):
    """ An external resource, configured before the application starts. """
    on = classmethod(partial)  # Decorator for engine command methods.

    def __call__(self, func):
        """ Used as a decorator, the function is called on change. """
        self.value = func
        self.deco = True
        return self

    def __set_name__(self, owner, name):
        """ Add a value setter command for the resource. """
        super().__set_name__(owner, name)
        cmdkey = f"res:{self.key}"
        Command(cmdkey, partialmethod(setattr, name)).__set_name__(owner, f"res{id(self)}")
        if self.deco:
            Command(cmdkey, self.value, **self.kwargs).__set_name__(owner, name)


class ComponentMeta(type):
    """ Metaclass for all subclasses of Component. """

    def __prepare__(name, bases):
        """ Add references to the command decorator and resource class for every component. """
        return {"on": Command.on, "resource": Resource}


class Component(metaclass=ComponentMeta):
    """ Base class for any component that sends and receives commands from the Spectra engine.
        It is the root class of the Spectra lexer object hierarchy, being subclassed directly
        or indirectly by nearly every important (externally-visible) piece of the program.
        As such, it cannot depend on anything except pure utility functions. """

    engine_call = nop  # Default engine callback is a no-op (useful for testing individual components).

    def engine_connect(self, engine_cb):
        """ Set the engine callback. """
        self.engine_call = engine_cb

    def __getstate__(self):
        """ Each component has a reference to the engine through self.engine_call, which respectively has a reference
            to almost everything else. Without intervention, if the pickler tries to pickle a component, it will
            follow the reference and attempt to pickle the engine, which results in pickling the entire program.
            Some parts are unavoidably unpickleable, so the reference chain must be stopped by removing engine_call.
            Unfortunately, this means no engine calls may be made by components after unpickling. """
        return {**vars(self), "engine_call": nop}
