from io import TextIOWrapper
from typing import AbstractSet, Iterable, Mapping, MutableMapping, MutableSequence, MutableSet

# Data types to treat as atomic (base types only). Do not look for children; display them as strings only.
_ATOMIC_TYPES = {type(None), bool, int, float, str, classmethod, staticmethod, type(lambda: None), TextIOWrapper}


class Container:
    """ A container of child objects in some manner, such as iterable contents or attributes. """

    # Data types/attributes and their corresponding containers.
    _TYPE_TABLE = []
    _ATTR_TABLE = []

    class TypeTuple(tuple):
        """ Tuple to sort classes by ancestry: child -> parent -> grandparent -> ... -> object. """
        def __lt__(self, other):
            return issubclass(self[0], other[0])

    def __init_subclass__(cls, tp:type=None, attr:str=None):
        """ Add each container under its type or attribute. Make sure subtypes are tested before base types. """
        if tp is not None:
            cls._TYPE_TABLE.append(cls.TypeTuple((tp, cls)))
            cls._TYPE_TABLE.sort()
        if attr is not None:
            cls._ATTR_TABLE.append((attr, cls))

    @classmethod
    def from_type(cls, obj) -> list:
        """ Determine the right container types based on an object's type and/or attributes and make a list of them. """
        if type(obj) in _ATOMIC_TYPES:
            return []
        for t, c in cls._TYPE_TABLE:
            if isinstance(obj, t):
                return [c(obj)]
        return [c(obj) for a, c in cls._ATTR_TABLE if hasattr(obj, a)]

    def __init__(self, obj):
        self._obj = obj

    def __len__(self) -> int:
        """ Return the number of items in the container. """
        raise NotImplementedError

    def __str__(self) -> str:
        return ""

    def __iter__(self) -> Iterable[tuple]:
        """ Whatever contents we have, they must be keyed in some way to return (k, v) tuples.
            Keep in mind that there could be thousands of items, or it could even be an infinite iterator.
            To be safe, return a lazy iterator so the program only evaluates items up to the child limit. """
        raise NotImplementedError


class MutableContainer(Container):

    def set(self, key, value):
        """ A container only has this method if it is mutable. """
        raise NotImplementedError


class ItemContainer(Container, tp=Iterable):
    """ An iterable item container. """

    def __len__(self) -> int:
        """ If the container has no len, it could be a consumable iterator, so don't allow expansion in that case. """
        try:
            return len(self._obj)
        except TypeError:
            return 0

    def __str__(self) -> str:
        """ Add the number of items to the type field if countable. """
        n = len(self)
        return f"{n} item" + "s" * (n != 1)

    def __iter__(self) -> Iterable[tuple]:
        """ For iterables such as sequences, automatically generate index numbers as the keys. """
        return enumerate(iter(self._obj))


class MutableItemContainer(ItemContainer, MutableContainer, tp=MutableSequence):

    def set(self, key, value):
        """ Set a container item by index/key. """
        self._obj[key] = value
        return key


class MappingContainer(ItemContainer, tp=Mapping):

    def __iter__(self) -> Iterable[tuple]:
        """ A mapping is shown in purest form with keys and values. """
        return iter(self._obj.items())


class MutableMappingContainer(MappingContainer, MutableItemContainer, tp=MutableMapping):
    pass


class SetContainer(ItemContainer, tp=AbstractSet):

    def __iter__(self) -> Iterable[tuple]:
        """ Sets behave mostly like sequences but are unordered. Use the hashes as indices to avoid confusion. """
        return zip(map(hash, self._obj), self._obj)


class MutableSetContainer(SetContainer, MutableContainer, tp=MutableSet):

    def set(self, key, value):
        """ The keys are hashes, so iterate through the items and replace the item with that hash. """
        for hs, item in self:
            if hs == key:
                self._obj.remove(item)
                self._obj.add(value)
                return hash(value)


class AttrContainer(MutableContainer, attr="__dict__"):

    def __len__(self):
        return len(self._obj.__dict__)

    def __iter__(self) -> Iterable[tuple]:
        """ Include an entry for the class (unless the object *is* a class) along with the instance attributes. """
        tp = type(self._obj)
        if tp is not type and hasattr(tp, "__dict__"):
            yield ("__class__", tp)
        yield from self._obj.__dict__.items()

    def set(self, key, value):
        """ setattr will fail on attributes such as data descriptors, but so will modifying __dict__ directly. """
        setattr(self._obj, key, value)
        return key
