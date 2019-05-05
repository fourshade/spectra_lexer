from functools import partial
from io import TextIOWrapper
from typing import Callable, Iterable, Iterator, List


class ContainerFactory:
    """ Registers and instantiates container classes that work with a particular property an object may have. """

    # Base data types to treat as atomic/indivisible. Looking for children in these is either wasteful or harmful.
    _ATOMIC_TYPES: set = {type(None), bool, int, float,  # Guaranteed to have no children.
                          str, bytes, bytearray,         # Children are just characters; do not expand these.
                          range, slice,                  # Pseudo-sequences have completely pre-determined children.
                          TextIOWrapper}                 # Expansion may crash if std streams are in use.

    _CLASSES: List[tuple] = []  # Keeps track of registered container classes.

    _cmp: Callable[[object, object], bool]
    _prop: object

    def __init__(self, cmp:Callable[[object, object], bool], prop:object):
        self._cmp = cmp
        self._prop = prop

    def __call__(self, tp:type) -> type:
        self._CLASSES.append((self._cmp, self._prop, tp))
        return tp

    @classmethod
    def containers(cls, obj:object) -> list:
        """ Return a list of containers from each independent container class that matches the object's properties.
            If any classes are in a direct inheritance line, only keep the most derived class. """
        if type(obj) in cls._ATOMIC_TYPES:
            return []
        matches = [c for cmp, prop, c in cls._CLASSES if cmp(obj, prop)]
        return [c(obj) for c in matches if sum([issubclass(m, c) for m in matches]) == 1]


class ContainerCollection(Iterable[List[dict]]):
    """ Creates "containers" which handle the iterable contents or attributes of an object. """

    _containers: List[Iterable[List[dict]]]

    def __init__(self, obj):
        """ Get a list of containers that matches the object's properties. """
        self._containers = ContainerFactory.containers(obj)

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


use_if_object_is = partial(ContainerFactory, isinstance)
use_if_object_has_attr = partial(ContainerFactory, hasattr)
