""" Base module of the Spectra lexer core package. Contains the most fundamental components. Don't touch anything...
    There are no type hints here. No type checker would stand a chance against all the descriptor voodoo. """

from collections import namedtuple
from functools import wraps
import sys
from typing import Callable, Dict, Iterable, List, Tuple, Type

from .command import Command, Resource
from .executor import Executor
from .package import NestedPackager, ListPackager, Packager
from spectra_lexer.types import delegate_to
from spectra_lexer.utils import nop, str_suffix, str_prefix


def pipe_to(key):
    def pipe_deco(func):
        @wraps(func)
        def call_next(self, *args, **kwargs):
            """ If there's a follow-up command and the output value wasn't None, run it. Return the original output. """
            value = func(self, *args, **kwargs)
            if value is not None:
                # Normal tuples (not subclasses) will be automatically unpacked into the next command.
                next_args = value if type(value) is tuple else (value,)
                self.engine_call(key, *next_args)
            return value
        return call_next
    return pipe_deco


class ComponentMeta(type):
    """ Metaclass for all subclasses of Component. """

    def __prepare__(name, bases):
        """ Add references to the main decorators to every component. """
        return {"on": Command, "pipe_to": pipe_to, "resource": Resource}


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


class CommandBinder(ListPackager):

    def bind(self, cmp:Component) -> List[Tuple[str, Callable]]:
        """ Return each bound command with its key from the component's class hierarchy.
            Save the raw commands that aren't initializers or resource setters for later introspection. """
        items = Command.get_all(cmp)
        self.update({k: m for k, m in items if ":" not in k})
        return [(k, m.bind(cmp)) for k, m in items]


class ResourceManager(NestedPackager):

    DELIM = ":"
    _PROVIDERS: Dict[Type[Component], str] = {}
    _DEPS: Dict[Type[Component], set] = {}

    class _Dependency(namedtuple("dep", "key requires")):
        """" Custom class for sorting dependencies. """
        def __lt__(self, other) -> bool:
            """ One resource must be loaded before another if its key appears in the other's requirement set. """
            return self.key in other.requires

    def load(self, cmp:Component) -> None:
        """ Add the first part of each resource identifier to the dependencies dict as a set. """
        items = Resource.get_all(cmp)
        self._DEPS[type(cmp)] = {str_prefix(key, ":") for key, _ in items}
        self.update(items)

    def add_provider(self, cmp:Component, key:str) -> None:
        """ Add a component to the provider dict under its type. """
        self._PROVIDERS[type(cmp)] = key

    def get_ordered_resources(self) -> list:
        """ Sort the resource types so that all dependencies are met in the right order. """
        deps = [self._Dependency(k, self._DEPS[tp]) for tp, k in self._PROVIDERS.items() if tp in self._DEPS]
        # Any keys in root but not in _PROVIDERS will be left out.
        # Those init commands will go unfulfilled *anyway* if no components provide them, so it's okay.
        ordered_keys = [dp.key for dp in sorted(deps)]
        d = self.to_dict()
        return [(k, d[k]) for k in ordered_keys if k in d]


class ModulePackager(NestedPackager):

    def __init__(self):
        super().__init__()
        self.update(sys.modules)


class ComponentParser(NestedPackager):

    def build(self, class_paths:Iterable[object]) -> List[Component]:
        """ Keep a global object dict indexed by module path. Only one object of each type may be present. """
        items = list(self._build(class_paths))
        self.update({str_suffix(str_prefix(type(cmp).__module__, ".base"), "."): cmp for cmp in items})
        return items

    def _build(self, class_paths:Iterable[object]) -> List[Component]:
        """ Create instances of all component classes found in the given paths.
            Paths may include classes, modules, and packages. The base class should never be instantiated.
            Prebuilt components may be included in the paths; they are yielded directly. """
        for path in class_paths:
            for obj in [path, *getattr(path, "__dict__", {}).values()]:
                if isinstance(obj, Component):
                    yield obj
                elif isinstance(obj, type) and issubclass(obj, Component):
                    yield obj()


class ComponentFactory(NestedPackager):
    """ Creates components from lists of component classes/modules (referred to as "class paths").
        Tracks every created component for introspection purposes. """

    _objects: Dict[str, Packager]
    _commands: CommandBinder
    _resources: ResourceManager

    def __init__(self):
        super().__init__()
        self._objects = d = {}
        self._components = d["components"] = ComponentParser()
        self._commands = d["commands"] = CommandBinder()
        self._resources = d["resources"] = ResourceManager()

    build = delegate_to("_components")

    def bind(self, components:Iterable[Component], engine_cb:Callable) -> Callable:
        """ Bind instances of component classes to their commands and resources with the engine callback.
            Return an executor callable with every bound command for the engine. """
        all_commands = []
        for cmp in components:
            cmp.engine_connect(engine_cb)
            self._resources.load(cmp)
            commands = self._commands.bind(cmp)
            all_commands += commands
            for key, _ in commands:
                # Tell the resource manager about any components that provide resources.
                if key.startswith("init:"):
                    self._resources.add_provider(cmp, key[5:])
        return Executor(all_commands)

    get_ordered_resources = delegate_to("_resources")

    def get_all_objects(self) -> Dict[str, dict]:
        """ Return a dict with objects from all categories for debug purposes. """
        d = self._objects
        d["modules"] = ModulePackager()
        return {k: v.to_dict() for k, v in d.items()}
