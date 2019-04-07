from functools import partial
from io import TextIOWrapper
from typing import Iterable, Iterator

from .container import Container, for_attr, for_type

# Data types to treat as atomic (base types only). Do not look for children; display them as strings only.
_ATOMIC_TYPES = {type(None), bool, int, float, str, classmethod, staticmethod, type(lambda: None), TextIOWrapper}


class ContainerCollection(Iterable):
    """ Creates "containers" which handle the iterable contents or attributes of an object. """

    _seq: Iterable[Container] = ()

    def __init__(self, obj):
        """ Determine the right container types based on an object's type and/or attributes and make a list of them. """
        self._tp = type(obj)
        if self._tp in _ATOMIC_TYPES:
            return
        self._seq = for_type.get_children(obj) + for_attr.get_children(obj)

    def __bool__(self) -> bool:
        return any(self._seq)

    def __str__(self) -> str:
        return " - ".join([self._tp.__name__, *filter(None, map(str, self._seq))])

    def __iter__(self) -> Iterator[tuple]:
        for c in self._seq:
            edit_cb = c.set
            for key, obj in c:
                children = ContainerCollection(obj)
                yield key, obj, children, edit_cb and partial(edit_cb, key)
