from collections import defaultdict
import sys

from spectra_lexer import Component
from spectra_lexer.utils import str_prefix, str_suffix


class ComponentFactory:
    """ Goes through a given list of modules and packages to find component classes, then creates one of each.
        Tracks every component made this way and creates dicts for introspection purposes. """

    _components: list       # List of all created components.
    _already_searched: set  # Set of IDs for all objects that have already been searched for component classes.

    def __init__(self):
        """ The base class should not be instantiated, so initialize the blacklist set with its ID. """
        self._components = []
        self._already_searched = {id(Component)}

    def __call__(self, classes_or_modules) -> list:
        """ Create instances of all component classes found in the given modules and packages.
            Only create ones we haven't seen before. Add them to the global list when finished. """
        new_components = []
        for m in classes_or_modules:
            for obj in (m, *vars(m).values()):
                if id(obj) not in self._already_searched:
                    self._already_searched.add(id(obj))
                    if isinstance(obj, type) and issubclass(obj, Component):
                        new_components.append(obj())
        self._components += new_components
        return new_components

    def make_debug_dict(self, **includes) -> dict:
        """ Make a global component dict indexed by module path to send to debug components.
            Add an access point for global modules, and arrange everything in tree-based packages. """
        cmp_by_path = {str_suffix(str_prefix(type(c).__module__, ".base"), "."): c for c in self._components}
        return {"__modules__": package(sys.modules), **includes, **package(cmp_by_path)}


class package(dict):
    """ Marker class used solely for packaging debug components and modules. """

    __slots__ = ()

    def __init__(self, src:dict, *, delim:str=".", root_name:str="__init__"):
        """ Split all keys in <src> on <delim> and build a nested dict arranged in a hierarchy based on these splits.
            If one key is a prefix of another, it may occupy a slot needed for another level of dicts.
            If this happens, that value will be moved one level deeper to the key <root_name>. """
        super().__init__()
        d = defaultdict(dict)
        for k, v in src.items():
            first, *rest = k.split(delim, 1)
            d[first][rest[0] if rest else root_name] = v
        for k, sect in d.items():
            if len(sect) == 1:
                self[k] = sect.popitem()[1]
            else:
                n = package(sect, delim=delim, root_name=root_name)
                if len(n) == 1:
                    rest, v = n.popitem()
                    self[k + delim + rest] = v
                else:
                    self[k] = n
