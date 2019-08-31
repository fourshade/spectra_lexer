""" Module for debug resources such as namespace dicts and data type icons. """

import csv
import pkgutil
import sys
from types import ModuleType
from typing import Any, Optional

from .data import DebugData


class package(dict):
    """ Dict for nesting objects and modules under path-like string keys. Has a special icon. """

    __slots__ = ()

    @classmethod
    def with_modules(cls, *args, **kwargs):
        """ Make a root package with args and kwargs as well as a nested representation of the loaded modules. """
        return cls(*args, **kwargs, modules=cls(sys.modules).nested())

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


class AutoImporter(dict):
    """ Namespace helper dict that functions as a copy of __builtins__ with extra features.
        It automatically tries to import missing modules any time code would otherwise throw a NameError.

        There is a separate namespace dict, within which the auto-importer is hidden as __builtins__.
        The auto-import dict, as with normal __builtins__, will be tried only after the namespace fails.
        The separate namespace is necessary; this class should *not* be used directly as an eval namespace.
        If it was, __missing__ on this object would be called *before* any builtin lookup was attempted.
        This would attempt a module import, and either outcome is terrible:
        - The import succeeds, in which case the builtin is now shadowed.
        - The import fails, which means the import machinery tried everything and failed.
          Doing this on *every* builtin access would be extremely expensive. """

    def __init__(self, *args, **kwargs) -> None:
        """ Start with a copy of the real global builtins dict and any kwargs. Add positional args to the namespace. """
        super().__init__(__builtins__, **kwargs)
        self.eval_namespace = dict(*args, __builtins__=self)  # Namespace for runtime evaluation of Python expressions.

    def __missing__(self, k:str) -> ModuleType:
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

    def eval(self, expr:str) -> Any:
        """ Evaluate the expression using the saved namespace dict. """
        return eval(expr, self.eval_namespace)


class DebugIcons:
    """ Container for SVG icon data representing various types of Python objects. """

    ICON_PACKAGE = __package__    # Name of Python package containing the file with all object tree icons.
    ICON_PATH = "/treeicons.dat"  # Relative path to icon file.

    def __init__(self) -> None:
        self._icons = {}  # Index of XML icon data keyed by the names of object data types.

    def load(self, package:str=ICON_PACKAGE, path:str=ICON_PATH) -> None:
        """ Parse the given icon resource as a CSV file. The first row contains only one field:
            the basic document structure with header and footer, usable as a format string.
            In all other rows, the last field is the SVG icon data itself, and every other field
            contains the name of a data type alias that uses the icon described by that data.
            Render each icon from packaged bytes data and add them to the dict under each alias. """
        data = pkgutil.get_data(package, path)
        lines = data.decode('utf-8').splitlines()
        [fmt], *items = csv.reader(map(str.strip, lines))
        for *aliases, xml_data in items:
            xml = fmt.format(xml_data).encode('utf-8')
            for n in aliases:
                self._icons[n] = xml

    def get_best(self, data:DebugData) -> Optional[bytes]:
        """ Return the best of the given available icons out of our sequence of choices from most wanted to least. """
        for k in data.icon_choices:
            if k in self._icons:
                return self._icons[k]
