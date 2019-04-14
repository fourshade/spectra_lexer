from typing import AbstractSet, Collection, Iterator, Mapping, MutableMapping, MutableSequence, MutableSet, Sequence

from .collection import for_property
from .container import Container, MutableContainer


class for_type(for_property):
    """ Decorator for classes that access items in a container of a specific data type. """

    def __init__(self, tp:type):
        self.tp = tp

    def __lt__(self, other) -> bool:
        """ Sort classes by ancestry: child -> parent -> grandparent -> ... -> object. """
        return issubclass(self.tp, other.tp)

    def __call__(self, cls:type) -> type:
        """ Add each container under its type. Make sure subtypes are tested before base types. """
        super().__call__(cls)
        self.PROP_TABLE.sort()
        return cls

    @classmethod
    def get_children(cls, obj) -> list:
        """ Return the first container in order that matches the object type, if any. """
        return next(([c(obj)] for self, c in cls.PROP_TABLE if isinstance(obj, self.tp)), [])


@for_type(Collection)
class SizedContainer(Container):
    """ A sized iterable item container. The most generic acceptable type of iterable container. """

    def __len__(self) -> int:
        """ Return the number of items in the container. Defaults to calling len() on the object. """
        return len(self._obj)

    def __str__(self) -> str:
        """ Add the number of items to the type field. """
        n = len(self)
        return f"{n} item" + "s" * (n != 1)


@for_type(Sequence)
class SequenceContainer(SizedContainer):

    def key_str(self, key) -> str:
        """ Add a dot in front of each index for clarity. """
        return f".{key}"


@for_type(MutableSequence)
class MutableSizedContainer(SequenceContainer, MutableContainer):
    pass


@for_type(Mapping)
class MappingContainer(SizedContainer):

    def kv_pairs(self) -> Iterator[tuple]:
        """ Mappings are shown with their natural keys and values. If under a certain size, attempt to sort it by key.
            A sort operation may fail if some elements aren't comparable. """
        pairs = self._obj.items()
        if len(self) < 200:
            try:
                # Since no two equal keys can exist in the same mapping, the values will never be tested.
                pairs = sorted(pairs)
            except TypeError:
                pass
        return iter(pairs)


@for_type(MutableMapping)
class MutableMappingContainer(MappingContainer, MutableContainer):
    pass


@for_type(AbstractSet)
class SetContainer(SizedContainer):

    def key_str(self, key) -> str:
        """ Sets behave mostly like sequences but are unordered. Display the hashes to avoid confusion. """
        return str(hash(key))

    def kv_pairs(self) -> Iterator[tuple]:
        """ The best way to find objects in a set is to let the objects themselves be the keys. """
        return zip(*[self._obj] * 2)


@for_type(MutableSet)
class MutableSetContainer(SetContainer, MutableContainer):

    def setitem(self, key, value) -> None:
        """ The key is the old item itself. Remove it and add the new item. """
        self._obj.discard(key)
        self._obj.add(value)
