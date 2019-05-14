from collections.abc import Iterable, Iterator
import pkgutil


class InstanceGroup(list):
    """ Recursive grouping of objects descended from common base types. """

    def __init__(self, class_paths:Iterable=(), *, whitelist=object, blacklist=()):
        super().__init__()
        self._whitelist = whitelist
        self._blacklist = blacklist
        self.add_from_paths(class_paths)

    def add_from_paths(self, class_paths:Iterable) -> None:
        """ Create and store instances of unique classes found in <class_paths>. """
        objects = [obj for path in class_paths for obj in self._iter_path(path)]
        classes = self._filter_classes(objects)
        unique = self._filter_unique(classes)
        self.extend([cls() for cls in unique])

    def _iter_path(self, path) -> Iterator:
        """ Class paths may include packages, modules, classes, and even instances (which are added as-is).
            If any paths are directly iterable, add them as distinct groups. """
        yield path
        if isinstance(path, Iterable):
            self.append(self.__class__(path, whitelist=self._whitelist, blacklist=self._blacklist))
        elif hasattr(path, "__file__"):
            yield from self._iter_module(path)

    def _iter_module(self, mod) -> Iterator:
        name = mod.__name__
        for v in vars(mod).values():
            if isinstance(v, type) and v.__module__ == name:
                yield v
        if hasattr(mod, "__path__"):
            yield from self._iter_package(mod)

    def _iter_package(self, pkg) -> Iterator:
        fromlist = [info.name for info in pkgutil.iter_modules(pkg.__path__)]
        __import__(pkg.__name__, globals(), locals(), fromlist)
        for k in fromlist:
            yield from self._iter_module(getattr(pkg, k))

    def _filter_classes(self, objects:Iterable) -> Iterator:
        """ Subclasses of any class in <whitelist> and none in <blacklist> will be instantiated. """
        for obj in objects:
            if isinstance(obj, type):
                if issubclass(obj, self._whitelist) and not issubclass(obj, self._blacklist):
                    yield obj
            elif isinstance(obj, self._whitelist):
                self.append(obj)

    def _filter_unique(self, classes:Iterable) -> list:
        """ A class and its descendants (including duplicates) may not exist in the same group.
            Keep only the "leaf" classes. If found, subclasses will replace their parent in order. """
        unique = []
        for cls in classes:
            for i, current in enumerate(unique):
                if issubclass(cls, current):
                    unique[i] = cls
                    break
            else:
                unique.append(cls)
        return unique

    def __str__(self) -> str:
        return ", ".join(type(c).__name__ for c in self.recurse_items())

    def recurse_items(self) -> Iterator:
        """ Recursively yield items only. Do not include intermediate containers. """
        for cmp in self:
            if isinstance(cmp, InstanceGroup):
                yield from cmp.recurse_items()
            else:
                yield cmp
