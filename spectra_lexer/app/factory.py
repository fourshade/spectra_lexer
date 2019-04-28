import sys
from collections import defaultdict
from typing import Iterable, List, Callable, Tuple

from spectra_lexer import Component
from spectra_lexer.base import ComponentMeta, Command, Resource
from spectra_lexer.utils import str_suffix, str_prefix


class package(dict):
    """ Class used for packaging components, markers, and modules. """

    DELIM: str = "."
    ROOT_NAME: str = "__init__"

    __slots__ = ()

    def expand(self):
        """ Split all keys on <_delim> and build a nested dict arranged in a hierarchy based on these splits.
            If one key is a prefix of another, it may occupy a slot needed for another level of dicts.
            If this happens, that value will be moved one level deeper to the key <_root_name>. """
        d = defaultdict(dict)
        for k, v in self.items():
            first, *rest = k.split(self.DELIM, 1)
            d[first][rest[0] if rest else self.ROOT_NAME] = v
        self.clear()
        for k, sect in d.items():
            if len(sect) == 1:
                self[k], = sect.values()
            else:
                n = self.__class__(sect).expand()
                if len(n) == 1:
                    (rest, v), = n.items()
                    self[k + self.DELIM + rest] = v
                else:
                    self[k] = n
        return self


class ComponentFactory(package):
    """ Creates components from lists of component classes/modules (referred to as "class paths").
        Tracks every created component for introspection purposes. """

    def __call__(self, class_paths:Iterable) -> List[Component]:
        """ Keep a global object dict indexed by module path. Only one object of each type may be present. """
        items = list(self.assemble(class_paths))
        for cmp in items:
            mod = type(cmp).__module__
            self[str_suffix(str_prefix(mod, ".base"), ".")] = cmp
        return items

    def assemble(self, class_paths:Iterable) -> List[Component]:
        """ Create instances of all component classes found in the given paths.
            Paths may include classes, modules, and packages. The base class should never be instantiated.
            Prebuilt components may be included in the paths; they are yielded directly. """
        for path in class_paths:
            for obj in [path, *getattr(path, "__dict__", {}).values()]:
                if isinstance(obj, Component):
                    yield obj
                elif isinstance(obj, ComponentMeta):
                    yield obj()


class CommandBinder(package):

    DELIM = ":"

    def bind(self, cmp:Component, engine_cb:Callable) -> List[Tuple[str, Callable]]:
        items = [(k, m.bind(cmp, engine_cb)) for k, m in Command.get_all(type(cmp))]
        for key, func in items:
            self.setdefault(key, []).append(func)
        return items


class ResourceBinder(package):

    DELIM = ":"

    def bind(self, cmp:Component) -> List[Tuple[str, Callable]]:
        items = Resource.get_all(type(cmp))
        self.update(items)
        return items

    def get_ordered(self):
        """ Sort the resource categories so that all dependencies are met in the right order. """
        return {k: self[k] for k in sorted(self)}


class ModulePackage(package):

    def expand(self):
        return package(sys.modules).expand()
