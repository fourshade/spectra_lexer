""" Base module of the Spectra core package. Contains the most fundamental classes. Don't touch anything... """

from collections import defaultdict
from functools import partial

from typing import Callable, Hashable, Iterable, List, Tuple

from spectra_lexer.types.dict import autodict
from spectra_lexer.utils import nop


class Component:
    """ Base class for any component that sends and receives commands from the Spectra engine.
        It is the root class of the Spectra lexer component hierarchy, being subclassed directly
        or indirectly by nearly every important (externally-visible) piece of the program. """

    engine_call = nop  # Default engine callback is a no-op (useful for testing individual components).

    def engine_connect(self, call:Callable) -> None:
        """ Connect this component to the engine callback. """
        self.engine_call = call

    def __getstate__(self) -> dict:
        """ Each component has a reference to the engine through self.engine_call, which respectively has a reference
            to almost everything else. Without intervention, if the pickler tries to pickle a component, it will
            follow the reference and attempt to pickle the engine, which results in pickling the entire program.
            Some parts are unavoidably unpickleable, so the reference chain must be stopped by removing engine_call.
            Unfortunately, this means no engine calls may be made by components after unpickling. """
        return {**vars(self), "engine_call": nop}


class AbstractMod:
    """ The golden rule of component mods is that the code must operate as if the mods did not exist when
        running without engine support (i.e. for unit tests). To that end, they must replace anything
        they decorate with either the original value or a default before the end of class creation.
        If any functions are permanently modified, pickling will fail, and so will multiprocessing. """

    _INSTANCES: dict = defaultdict(list)  # Class-specific dict of instances keyed by owner component class.

    cmd_key: Hashable = None
    _attr: str = None          # The attribute name assigned to this mod on the component class.

    def __init_subclass__(cls):
        """ Add a data dict with component classes as keys and lists of mod instances as values. """
        cls._INSTANCES = defaultdict(list)

    def __set_name__(self, owner:type, name:str) -> None:
        """ Add the instance to the class data dicts and save the attribute name. """
        cls = type(self)
        for base in cls.__mro__[:-1]:
            base._INSTANCES[owner].append(self)
        self._attr = name

    @classmethod
    def lookup(cls, cmp:object) -> list:
        """ Return each mod of type <cls> owned by <cmp>'s class hierarchy. """
        return [(m.cmd_key, m) for subcls in type(cmp).__mro__ for m in cls._INSTANCES[subcls]]

    @classmethod
    def bind_all(cls, cmp:object) -> List[Tuple[Hashable, Callable]]:
        """ Bind a component to mods from its class hierarchy and return the commands. """
        return [(k, m.cmd_func(cmp)) for k, m in cls.lookup(cmp)]

    def cmd_func(self, cmp:object) -> Callable:
        raise NotImplementedError


class AbstractCommand(AbstractMod):

    def cmd_func(self, cmp:object) -> Callable:
        """ Return a final callable to dynamically bind the component instance. """
        def call(*args, _attr=self._attr, **kwargs):
            return getattr(cmp, _attr)(*args, **kwargs)
        return call


class Command(AbstractCommand):
    """ Simple command where the method itself is the key, replaced on __set_name__. """

    def __init__(self, func:Hashable):
        self.cmd_key = self


class AbstractSignal(AbstractMod):
    """ Command where the key is the owner class. Only one can exist per base class, but it makes inheritance easy. """

    def __set_name__(self, owner:type, name:str) -> None:
        self.cmd_key = owner
        super().__set_name__(owner, name)


class Signal(AbstractSignal, Command):
    """ One-way signal that another class receives by subclassing and implementing it. """


class AbstractResource(AbstractMod):
    """ An external resource using a hashable key that stores its value on the component. """

    _RES_ATTRS: dict = defaultdict(set)

    def cmd_func(self, cmp) -> Callable:
        """ Store the provided value on command call and add this mod to the required resources.
            If the component attempts to start before all resources are loaded, suppress it. """
        cmp.on_app_start = partial(delattr, cmp, "on_app_start")
        attrs = self._RES_ATTRS[id(cmp)]
        attrs.add(self)
        def set_resource(value):
            """ Set a resource value and remove self from the set, if present. """
            setattr(cmp, self._attr, value)
            attrs.discard(self)
            # If the set is now empty, all resources must be ready.
            if not attrs:
                # If the start method has not been run yet, delete the instance attribute to allow access.
                # If it *has* been run, that attribute will have deleted itself. In that case, run it for real.
                if "on_app_start" in vars(cmp):
                    del cmp.on_app_start
                elif hasattr(cmp, "on_app_start"):
                    cmp.on_app_start()
        return set_resource


class Resource(AbstractSignal, AbstractResource):
    pass


class Option(AbstractResource):

    info: tuple  # Option info to return on init.

    def __init__(self, *args:Hashable, default=None, desc:str=""):
        """ Include an optional description for introspection tools. """
        self.cmd_key = self.response(*args)
        self.info = default, desc

    def __set_name__(self, owner:type, name:str) -> None:
        """ Put the default value back. """
        super().__set_name__(owner, name)
        setattr(owner, name, self.info[0])

    @classmethod
    def init_info(cls):
        return Option(cls)

    @classmethod
    def response(cls, *args:Hashable):
        return (cls, *args)

    @classmethod
    def setup_commands(cls, components:Iterable[object]) -> List[Tuple[Hashable, dict]]:
        """ Return all required initialization commands and their items. """
        d = autodict()
        for cmp in components:
            for k, m in cls.lookup(cmp):
                d.traverse_setitem(k, m)
        return [(Option.response(k), d[k]) for k in d]


class CommandClass(autodict):

    def __init__(self, **fields):
        """ For now, only the values (and count) of the fields are actually used. """
        super().__init__()
        self.defaults = tuple(fields.values())

    def __call__(self, *args) -> Callable:
        """ Capture a single command, with optional partial positional args. """
        count = len(self.defaults)
        argc = len(args)
        if argc < count:
            args = args + self.defaults[argc:]
        def capture(fn:Callable=None) -> Command:
            """ Any leftover args are used as partials. """
            if argc > count:
                fn = partial(fn, *args[count:])
            cmd = Command(fn)
            self.traverse_setitem(args[:count], cmd.cmd_key)
            return cmd
        return capture
