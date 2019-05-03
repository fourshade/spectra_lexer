from functools import partial
from typing import Callable

from .deps import DependencyOrderer
from .packaged import PackagedMod
from spectra_lexer.types import package
from spectra_lexer.utils import str_prefix


class ResourceMod(PackagedMod):

    provides: str = None
    requires: str = None

    @classmethod
    def make_package(cls) -> package:
        """ Make a package that contains only resource mods that require something (not provide it).
            With no root key, any info for resources that contain other resources is discarded.
            Broadcast will still allow these components to receive resource packages. """
        return package([(m.pkg_key, m) for m in cls.lookup_mods() if m.requires is not None], delim=":")

    @classmethod
    def setup(cls, engine_call:Callable) -> None:
        """ Sort the resource types so that all dependencies are met in the right order.
            Use the first part of each resource identifier as a key. Initialize all resources in order at the end. """
        deps = DependencyOrderer()
        for tp in cls.lookup_owners():
            requires = {m.requires for m in cls.lookup_by_owner(tp) if m.requires is not None}
            provides = {m.provides for m in cls.lookup_by_owner(tp) if m.provides is not None}
            deps.add_object(tp, requires, provides)
        pkg = cls.make_package()
        for k in deps.sorted_keys():
            engine_call(f"init:{k}", pkg[k])


class ResourceInitializer(ResourceMod, key="init"):

    def __init__(self, key:str):
        """ The command always starts with 'init:'. """
        self.cmd_key = f"init:{key}"
        self.provides = key


class ResourceDef(ResourceMod, key="on_resource", package_key="resources"):
    """ An external resource, configured before the application starts.
        It is like a command, but is required to be called before the component may be used. """

    def __init__(self, key:str):
        """ The command always starts with 'res:'. """
        self.cmd_key = f"res:{key}"
        self.pkg_key = key
        self.requires = str_prefix(key, ":")


class StoredResourceDef(ResourceDef, key="resource"):
    """ An external resource that stores its value on the component without calling a function on it.
        It includes a default value and optionally a description for introspection tools. """

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
