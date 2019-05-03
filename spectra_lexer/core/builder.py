from typing import Iterable, Iterator, List

from spectra_lexer.types import package


class ClassBuilder:
    """ Constructor class that searches modules for a class and its descendants, building them if found. """

    _object_list: List[object]  # List of all objects created (or found pre-created).
    _search_cls: type           # Base class to search modules for.

    def __init__(self, search_cls:type):
        self._object_list = []
        self._search_cls = search_cls

    def build(self, class_paths:Iterable[object]) -> list:
        items = list(self._search(class_paths))
        self._object_list += items
        return items

    def _search(self, class_paths:Iterable[object]) -> Iterator:
        """ Create instances of all subclasses found in the given paths. Paths may include classes and modules.
            Prebuilt objects may be included in the paths; they are yielded directly if of the correct type. """
        search_cls = self._search_cls
        for path in class_paths:
            for obj in [path, *getattr(path, "__dict__", {}).values()]:
                if isinstance(obj, search_cls):
                    yield obj
                elif isinstance(obj, type) and issubclass(obj, search_cls):
                    yield obj()

    def package(self) -> package:
        """ Return a package with each object indexed by its class's module path. """
        d = {_module_key(cmp): cmp for cmp in self._object_list}
        return package(d, root_key="__init__")


def _module_key(obj:object) -> str:
    """ Get a key to index an object by its class's module path. """
    ks = type(obj).__module__.split(".")
    if ks[-1] == "base":
        ks.pop()
    return ".".join(ks[1:])
