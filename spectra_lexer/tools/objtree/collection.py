from io import TextIOWrapper
from typing import Iterable, Iterator, List


class ContainerCollection(Iterable[List[dict]]):
    """ Creates "containers" which handle the iterable contents or attributes of an object. """

    _containers: list
    type_str: str

    def __init__(self, obj):
        """ Determine the right container types based on an object's type and/or attributes and make a list of them. """
        self._containers = for_property.get_all_children(obj)
        self.type_str = " - ".join([type(obj).__name__, *filter(None, map(str, self._containers))])

    def __bool__(self) -> bool:
        return any(self._containers)

    def __iter__(self) -> Iterator[List[dict]]:
        """ Yield items from each container in turn. """
        for c in self._containers:
            yield from c


class for_property:
    """ Base class for decorators that keep track of containers working on a particular property an object may have. """

    # Base data types to treat as atomic/indivisible. Looking for children in these is either wasteful or harmful.
    _ATOMIC_TYPES: set = {type(None), bool, int, float,  # Guaranteed to have no children.
                          str, bytes, bytearray,         # Children are just characters; do not expand these.
                          TextIOWrapper}                 # Expansion may crash if std streams are in use.
    _CLASSES: list = []    # Keeps track of decorator subclasses.
    PROP_TABLE: list = []  # Each decorator subclass has one of these. Keeps track of registered container classes.

    def __init_subclass__(cls, *args, **kwargs):
        """ Add the subclass to the list and make a new table for container classes with the desired property. """
        super().__init_subclass__(*args, **kwargs)
        cls._CLASSES.append(cls)
        cls.PROP_TABLE = []

    def __call__(self, cls:type) -> type:
        """ Add each container to the table with its decorator object. """
        self.PROP_TABLE.append((self, cls))
        return cls

    @classmethod
    def get_all_children(cls, obj) -> list:
        """ Return all child containers that match certain properties of the object and contain at least one item. """
        if type(obj) in cls._ATOMIC_TYPES:
            return []
        return [child for tp in cls._CLASSES for child in filter(None, tp.get_children(obj))]
