from typing import Iterable, List, Callable, Tuple

from .package import package
from spectra_lexer import Component
from spectra_lexer.base import Command, Resource
from spectra_lexer.utils import str_suffix, str_prefix


class ComponentFactory(package):
    """ Creates components from lists of component classes/modules (referred to as "class paths").
        Tracks every created component for introspection purposes. """

    def __call__(self, class_paths:Iterable) -> List[Component]:
        """ Keep a global object dict indexed by module path. Only one object of each type may be present. """
        items = list(self._assemble(class_paths))
        for cmp in items:
            mod = type(cmp).__module__
            self.set_nested(str_suffix(str_prefix(mod, ".base"), "."), cmp)
        return items

    def _assemble(self, class_paths:Iterable) -> List[Component]:
        """ Create instances of all component classes found in the given paths.
            Paths may include classes, modules, and packages. The base class should never be instantiated.
            Prebuilt components may be included in the paths; they are yielded directly. """
        for path in class_paths:
            for obj in [path, *getattr(path, "__dict__", {}).values()]:
                if isinstance(obj, Component):
                    yield obj
                elif isinstance(obj, type) and issubclass(obj, Component):
                    yield obj()


class CommandBinder(dict):

    def bind(self, cmp:Component, engine_cb:Callable) -> List[Tuple[str, Callable]]:
        items = [(k, m.bind(cmp, engine_cb)) for k, m in Command.get_all(type(cmp))]
        for key, func in items:
            self.setdefault(key, []).append(func)
        return items


class ResourceBinder(package):

    DELIM = ":"

    def bind(self, cmp:Component) -> List[Tuple[str, Callable]]:
        items = Resource.get_all(type(cmp))
        self.update_nested(items)
        return items

    def get_ordered(self):
        """ Sort the resource categories so that all dependencies are met in the right order. """
        return {k: self[k] for k in sorted(self)}
