""" Module for Python system-specific classes involving modules and packages. """

import pkgutil
import sys
from types import ModuleType


class AutoImporter(dict):
    """ Namespace helper dict that functions as a copy of __builtins__ with extra features.
        It automatically tries to import missing modules any time code would otherwise throw a NameError.

        It should *not* be passed directly to eval/exec as the global namespace. If it is, __missing__ will be called
        *before* any builtin lookup is attempted. This attempts a module import, and either outcome is terrible:
        - The import succeeds, in which case the builtin is now shadowed.
        - The import fails, which means the import machinery tried everything and failed.
          Doing this on *every* builtin access is extremely expensive. """

    __slots__ = ()

    def _import(self, k:str) -> ModuleType:
        return __import__(k, self, locals(), [])

    def __missing__(self, k:str) -> ModuleType:
        """ Try to import missing modules before raising a KeyError (which becomes a NameError).
            If successful, attempt to import submodules recursively. """
        try:
            module = self[k] = self._import(k)
        except Exception:
            raise KeyError(k) from None
        try:
            for finder, name, ispkg in pkgutil.walk_packages(module.__path__, k + '.'):
                self._import(name)
        except Exception:
            pass
        return module

    @classmethod
    def eval_namespace(cls, *args, **kwargs) -> dict:
        """ Make a globals namespace dict for eval(), within which an auto-importer will function as __builtins__. """
        return dict(*args, __builtins__=cls(__builtins__), **kwargs)


class package(dict):
    """ Dict for nesting objects (specifically Python modules) under path-like string keys. Has a special icon. """

    __slots__ = ()

    @classmethod
    def nested(cls, src:dict, delim:str, root_key:str) -> "package":
        """ Split all keys in <src> on <delim> and nest package dicts in a hierarchy based on these splits.
            If one key is a prefix of another, it may occupy a slot needed for another level of dicts.
            If this happens, move the value one level deeper under <root_key>. """
        pkg = cls()
        for k, v in src.items():
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

    @classmethod
    def from_modules(cls) -> "package":
        """ Return a new package with a nested representation of the currently loaded modules. """
        return cls.nested(sys.modules, delim=".", root_key="__init__")
