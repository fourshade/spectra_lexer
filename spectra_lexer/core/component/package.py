class package(dict):
    """ Simple marker class for object package dicts. May gain functionality in the future. """
    __slots__ = ()


class Packager:

    _root: package

    def __init__(self):
        self._root = package()

    def update(self, d) -> None:
        items_iter = getattr(d, "items", d.__iter__)()
        self._update(items_iter)

    def _update(self, items_iter) -> None:
        raise NotImplementedError

    def to_dict(self) -> package:
        """ Return the root dict directly. Subclasses may do more processing. """
        return self._root


class NestedPackager(Packager):
    """ Class for packaging components, markers, and modules under string keys in a nested dict. """

    DELIM: str = "."
    ROOT_NAME: str = "__init__"

    def _update(self, items_iter) -> None:
        """ Split all keys on <DELIM> and nest package dicts in a hierarchy based on these splits.
            If one key is a prefix of another, it may occupy a slot needed for another level of dicts.
            If this happens, move that value one level deeper to the key <ROOT_NAME>. """
        root = self._root
        delim = self.DELIM
        root_name = self.ROOT_NAME
        for k, v in items_iter:
            d = root
            *first, last = k.split(delim)
            for i in first:
                if i not in d:
                    d[i] = package()
                elif not isinstance(d[i], package):
                    d[i] = package({root_name: d[i]})
                d = d[i]
            if last not in d or not isinstance(d[last], package):
                d[last] = v
            else:
                d[last][root_name] = v


class ListPackager(Packager):
    """ Class for packaging objects in lists under string keys, which allows duplicates. """

    def _update(self, items_iter) -> None:
        d = self._root
        for k, v in items_iter:
            d.setdefault(k, []).append(v)
