from functools import partial
from typing import Callable, Iterable

from .base import ComponentMod, MainMod
from .command import CommandMod, CommandDef
from .deps import DependencyOrderer
from .package import package
from spectra_lexer.utils import str_prefix


class ResourceMod(ComponentMod):

    provides: str = None
    requires: str = None

    @classmethod
    def setup(cls, components:Iterable, engine_call:Callable) -> None:
        """ Sort the resource types so that all dependencies are met in the right order.
            Use the first part of each resource identifier as a key.
            Initialize all resources in order at the end with the main engine callback. """
        deps = DependencyOrderer()
        pkg = package()
        for cmp in components:
            mods = cls.lookup_cmp_mods(cmp)
            reqs = {m.requires: m for m in mods}
            reqs.pop(None, None)
            pkg.update(reqs)
            deps.add_requirements({m.provides for m in mods} - {None},
                                  {str_prefix(r, ":") for r in reqs})
        pkg.nest(delim=":")
        for k in deps.sorted_keys():
            engine_call(f"init:{k}", pkg[k])


class ResourceInit(MainMod, CommandMod, ResourceMod):

    KEY = "init"

    def __init__(self, key:str):
        """ The command always starts with 'init:'. """
        self.cmd_key = f"init:{key}"
        self.provides = key


class ResourceDef(CommandDef, ResourceMod):
    """ An external resource, configured before the application starts.
        It is like a command, but is required to be called before the component may be used. """

    KEY = "on_resource"
    DEBUG_KEY = "resources"
    NEST_KWARGS = {"delim": ":"}

    def __init__(self, key:str):
        """ The command always starts with 'res:'. """
        super().__init__(key)
        self.cmd_key = f"res:{key}"
        self.requires = self.pkg_key = key


class StoredResourceDef(ResourceDef):
    """ An external resource that stores its value on the component without calling a function on it.
        It includes a default value and optionally a description for introspection tools. """

    KEY = "resource"

    _desc: str

    def __init__(self, key:str, value=None, desc:str=""):
        """ The value is a default setting for the resource. """
        super().__init__(key)
        self._value = value
        self._desc = desc

    def bind(self, cmp:object) -> Callable:
        """ Store the provided value on command call. """
        return partial(setattr, cmp, self._attr)

    def info(self) -> tuple:
        """ Return the option info. """
        return self._value, self._desc
