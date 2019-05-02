from typing import Iterable, List, Callable, Tuple

from spectra_lexer import Component
from spectra_lexer.base import ComponentMeta, Command, Resource
from spectra_lexer.utils import str_suffix, str_prefix


class ComponentAssembler(dict):
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


class CommandBinder(dict):

    def bind(self, cmp:Component, engine_cb:Callable) -> List[Tuple[str, Callable]]:
        items = [(k, m.bind(cmp, engine_cb)) for k, m in Command.get_all(type(cmp))]
        for key, func in items:
            self.setdefault(key, []).append(func)
        return items


class ResourceBinder(dict):

    def bind(self, cmp:Component) -> List[Tuple[str, Callable]]:
        items = Resource.get_all(type(cmp))
        for key, res in items:
            if ":" in key:
                src, sect = key.split(":", 1)
                self.setdefault(src, {})[sect] = res
            else:
                self[key] = res
        return items

    def get_ordered(self):
        """ Sort the resource categories so that all dependencies are met in the right order. """
        return dict(sorted(self.items(), key=lambda x: x[0]))
