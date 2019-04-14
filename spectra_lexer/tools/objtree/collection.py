from io import TextIOWrapper
from typing import Iterable, Iterator, List


class ContainerCollection(Iterable[List[dict]]):
    """ Creates "containers" which handle the iterable contents or attributes of an object. """

    # Base data types to treat as atomic/indivisible. Looking for children in these is either wasteful or harmful.
    _ATOMIC_TYPES: set = {type(None), bool, int, float,  # Guaranteed to have no children.
                          str, bytes, bytearray,         # Children are just characters; do not expand these.
                          range, slice,                  # Pseudo-sequences have completely predictable children.
                          TextIOWrapper}                 # Expansion may crash if std streams are in use.
    _CLASSES: List[tuple] = []     # Keeps track of registered container classes.

    _containers: List[Iterable[List[dict]]] = []

    def __init__(self, obj):
        """ Make a list of containers from each independent container class that matches the object's properties.
            If any classes are in a direct inheritance line, only keep the most derived class. """
        if type(obj) in self._ATOMIC_TYPES:
            return
        matches = [c for cmp, prop, c in self._CLASSES if cmp(obj, prop)]
        self._containers = [c(obj) for c in matches if sum([issubclass(m, c) for m in matches]) == 1]

    def __bool__(self) -> bool:
        """ The collection has items if any container does. """
        return any(self._containers)

    def __str__(self) -> str:
        """ Return the string with the total number of items in the containers. May be empty. """
        return ", ".join(filter(None, map(str, self._containers)))

    def __iter__(self) -> Iterator[List[dict]]:
        """ Yield items from each container in turn. """
        for c in self._containers:
            yield from c

    @classmethod
    def register_property(cls, cmp, prop):
        """ Register a container class that acts on on a particular property an object may have. """
        def add_entry(tp:type) -> type:
            cls._CLASSES.append((cmp, prop, tp))
            return tp
        return add_entry


use_if = ContainerCollection.register_property
