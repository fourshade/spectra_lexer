from collections import defaultdict
import sys
from typing import Dict, Iterable

from .base import AbstractMod


class package(dict):
    """ Class for packaging objects and modules under string keys in a nested dict.
        Items are stored as with a normal dict, then converted to nested form only when needed. """

    __slots__ = ()

    def nest(self, delim:str=" ", root_key:str=None) -> None:
        """ Split all keys on <delim> and nest package dicts in a hierarchy based on these splits.
            If one key is a prefix of another, it may occupy a slot needed for another level of dicts.
            If this happens and <root_key> is None, destroy its value to make room for the new dicts.
            If <root_key> is not None, move the value one level deeper under that key. """
        items = list(self.items())
        self.clear()
        for k, v in items:
            d = self
            *first, last = k.split(delim)
            for i in first:
                if i not in d:
                    d[i] = package()
                elif not isinstance(d[i], package):
                    r = d[i]
                    d[i] = package()
                    if root_key is not None:
                        d[i][root_key] = r
                d = d[i]
            if last not in d or not isinstance(d[last], package):
                d[last] = v
            elif root_key is not None:
                d[last][root_key] = v


class DebugPackageMod(AbstractMod):

    DEBUG_KEY: str
    NEST_KWARGS: dict = {"delim": ".", "root_key": "__init__"}

    @classmethod
    def package_all(cls, components:Iterable) -> Dict[str, package]:
        """ Return a debug dict with packages from all packaged mod classes.
            If any packages have the same key due to subclassing, merge them. """
        d = {}
        pkgs = defaultdict(package)
        for subcls in cls.subclasses():
            k = subcls.DEBUG_KEY
            d[k] = subcls
            pkgs[k].update(subcls.package_items(components))
        for k in sorted(d):
            pkgs[k].nest(**d[k].NEST_KWARGS)
        return pkgs

    @classmethod
    def package_items(cls, components:Iterable) -> Iterable:
        raise NotImplementedError


class ComponentPackager(DebugPackageMod):

    DEBUG_KEY = "components"

    @classmethod
    def package_items(cls, components:Iterable) -> Iterable:
        """ Yield package items with each component indexed by its class's module path. """
        for cmp in components:
            ks = type(cmp).__module__.split(".")
            if ks[-1] == "base":
                ks.pop()
            yield ".".join(ks[1:]), cmp


class ModulePackager(ComponentPackager):

    DEBUG_KEY = "modules"

    @classmethod
    def package_items(cls, components:Iterable) -> Iterable:
        return sys.modules
