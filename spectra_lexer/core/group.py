import pkgutil
from typing import Iterable, Iterator


class ClassFilter:
    """ Uses a whitelist and/or blacklist to filter objects by instance or subclass. """

    def __init__(self, whitelist=object, blacklist=()):
        self._whitelist = whitelist
        self._blacklist = blacklist

    def instances(self, objects:Iterable) -> list:
        """ Return objects which are instances of anything in <whitelist> and nothing in <blacklist>. """
        return [obj for obj in objects if isinstance(obj, self._whitelist) and not isinstance(obj, self._blacklist)]

    def classes(self, objects:Iterable) -> list:
        """ Return objects which are subclasses of anything in <whitelist> and nothing in <blacklist>. """
        return [obj for obj in objects if isinstance(obj, type)
                and issubclass(obj, self._whitelist) and not issubclass(obj, self._blacklist)]

    def most_derived(self, classes:Iterable[type]) -> list:
        """ Filter an iterable of classes to eliminate ancestors and duplicates.
            Keep only the 'most derived' classes, i.e. those with no subclasses of their own in the iterable. """
        unique = []
        for cls in classes:
            for i, current in enumerate(unique):
                # Subclasses will replace ancestors *in order*.
                if issubclass(cls, current):
                    unique[i] = cls
                    break
            else:
                unique.append(cls)
        return unique


class InstanceGroup(list):
    """ List of instance objects created from classes found in paths. """

    def __init__(self, class_paths, class_filter:ClassFilter):
        """ Create and store instances of the most derived classes found in <class_paths>. """
        objects = [obj for path in class_paths for obj in self._iter_path(path)]
        classes = class_filter.classes(objects)
        derived = class_filter.most_derived(classes)
        super().__init__([cls() for cls in derived])

    def _iter_path(self, path) -> Iterator:
        """ Class paths may include packages, modules, and classes. """
        yield path
        if hasattr(path, "__file__"):
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

    def __str__(self) -> str:
        return str([type(c).__name__ for c in self])
