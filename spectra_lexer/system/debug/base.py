import csv
import pkgutil
import sys
from typing import Any, Dict

from .data import DebugData
from .factory import DataFactory


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


class DebugTree:

    ICON_PATH = (__package__, "/treeicons.dat")  # Package and relative file path with all object tree icons.

    _root_dict: dict       # Mapping at the top level of the tree diagram.
    _eval_namespace: dict  # Namespace for runtime evaluation of user expressions.

    def __init__(self, root_dict:dict, eval_namespace:dict=None, **kwargs):
        """ Add kwargs as well as a nested representation of the loaded modules to the root dict. """
        root_dict.update(kwargs, modules=package(sys.modules).nested())
        self._root_dict = root_dict
        self._eval_namespace = eval_namespace or {}

    def data(self) -> DebugData:
        """ Make a data item corresponding to the root dict. It is the only data item without any container. """
        return DataFactory().generate(self._root_dict)

    @classmethod
    def icons(cls) -> Dict[str, bytes]:
        """ Parse the root icon resource as a CSV file. The first row contains only one field:
            the basic document structure with header and footer, usable as a format string.
            In all other rows, the last field is the SVG icon data itself, and every other field
            contains the name of a data type alias that uses the icon described by that data.
            Render each icon from packaged bytes data and add them to a dict under each alias. """
        icons = {}
        data = pkgutil.get_data(*cls.ICON_PATH)
        lines = data.decode('utf-8').splitlines()
        [fmt], *items = csv.reader(map(str.strip, lines))
        for *aliases, xml_data in items:
            xml = fmt.format(xml_data).encode('utf-8')
            for n in aliases:
                icons[n] = xml
        return icons

    def eval(self, expr:str) -> Any:
        """ Evaluate the expression using the namespace dict given at creation. """
        return eval(expr, self._eval_namespace)
