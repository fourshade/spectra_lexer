from pkgutil import iter_modules
from typing import Iterable, Iterator, List

from .component import Component

BASE_CLASS = Component


class ComponentGroup(Iterable):
    """ Recursive grouping of components descended from a common base type. """

    _items: List[BASE_CLASS]
    _groups: List[Iterable]

    def __init__(self, class_paths:Iterable):
        """ Create and include instances of all subclasses of Component found in <class_paths>.
            Class paths may include packages, modules, and classes themselves.
            If any paths are directly iterable, treat them as distinct groups. """
        self._groups = []
        self._items = []
        seen = {BASE_CLASS}
        for path in class_paths:
            if isinstance(path, Iterable):
                self._groups.append(self.__class__(path))
            elif isinstance(path, BASE_CLASS):
                self._items.append(path)
            else:
                for obj in self._iter_path(path):
                    if isinstance(obj, type) and issubclass(obj, BASE_CLASS) and obj not in seen:
                        seen.add(obj)
                        self._items.append(obj())

    def _iter_path(self, path):
        yield path
        if hasattr(path, "__file__"):
            yield from self._iter_module(path)

    def _iter_module(self, mod):
        if hasattr(mod, "__path__"):
            yield from self._iter_package(mod)
        for obj in vars(mod).values():
            yield obj

    def _iter_package(self, pkg):
        fromlist = [info.name for info in iter_modules(pkg.__path__)]
        __import__(pkg.__name__, globals(), locals(), fromlist)
        for k in fromlist:
            yield from self._iter_module(getattr(pkg, k))

    def __iter__(self) -> Iterator[BASE_CLASS]:
        """ Recursively iterate over our contents to yield each item. """
        for cmp in self._items:
            yield cmp
        for grp in self._groups:
            yield from grp

    def split(self) -> Iterator[Iterable]:
        """ Yield groups from the first level of contents. Singular items are put into one-item groups. """
        for cmp in self._items:
            yield self.__class__([cmp])
        for grp in self._groups:
            yield grp

    def __str__(self) -> str:
        return ", ".join(type(c).__name__ for c in self)
