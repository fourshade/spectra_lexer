import pkgutil
import sys


class package(dict):
    """ Class for packaging objects and modules under string keys in a nested dict. """

    __slots__ = ()

    def nested(self, delim:str=".", root_key:str="__init__"):
        """ Split all keys on <delim> and nest package dicts in a hierarchy based on these splits.
            If one key is a prefix of another, it may occupy a slot needed for another level of dicts.
            If this happens, move the value one level deeper under <root_key>. """
        cls = self.__class__
        pkg = cls()
        for k, v in self.items():
            d = pkg
            *first, last = k.split(delim)
            for i in first:
                if i not in d:
                    d[i] = cls()
                elif not isinstance(d[i], cls):
                    d[i] = cls({root_key: d[i]})
                d = d[i]
            if last not in d or not isinstance(d[last], cls):
                d[last] = v
            else:
                d[last][root_key] = v
        return pkg


class AutoImporter(package):
    """ Interpreter namespace dict that functions as a copy of __builtins__ with extra features.
        It automatically tries to import missing modules any time code would otherwise throw a NameError. """

    __slots__ = ()

    def __missing__(self, k:str):
        """ Try to import missing modules before raising a KeyError (which becomes a NameError).
            If successful, attempt to import submodules recursively. """
        try:
            module = self[k] = __import__(k, self, locals(), [])
        except Exception:
            raise KeyError(k)
        try:
            for finder, name, ispkg in pkgutil.walk_packages(module.__path__, f'{k}.'):
                __import__(name, self, locals(), [])
        except Exception:
            pass
        return module


class DebugDict(dict):
    """ Debug namespace dict that automatically imports top-level modules for convenience. """

    __slots__ = ()

    def __init__(self, components:list, **kwargs):
        """ Auto-import tends to pollute namespaces with tons of garbage. We don't need that at the top level.
            The actual auto-import dict is hidden as __builtins__, and is tried only after the main dict fails. """
        # The class constructor will copy the real global builtins dict; it won't be corrupted.
        super().__init__(kwargs, __builtins__=AutoImporter(__builtins__))
        self._add_info(components)

    def _add_info(self, components:list) -> None:
        """ Make directories containing the given components and all currently loaded modules.
            Each component is indexed by its class's module path. Do not include the root package name.
            A 'base' module represents its entire package, as does one with the same name as the package. """
        d = self["components"] = package()
        for cmp in components:
            ks = type(cmp).__module__.split(".")
            if len(ks) > 1 and ks[-1] in (ks[-2], "base"):
                ks.pop()
            d["_".join(ks[1:])] = cmp
        self["modules"] = package(sys.modules).nested()
