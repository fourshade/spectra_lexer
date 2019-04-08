from typing import AbstractSet, Iterable, Iterator, List, Mapping, MutableMapping, MutableSequence, MutableSet


class Container:
    """ A container of child objects in some manner, such as iterable contents or attributes. """

    def __init__(self, obj):
        self._obj = obj

    def __len__(self) -> int:
        """ Return the number of items in the container. """
        raise NotImplementedError

    def __str__(self) -> str:
        return ""

    def __iter__(self) -> Iterator[tuple]:
        """ Whatever contents we have, they must be keyed in some way to return (k, v) tuples.
            Keep in mind that there could be thousands of items, or it could even be an infinite iterator.
            To be safe, return a lazy iterator so the program only evaluates items up to the child limit. """
        raise NotImplementedError

    def color(self) -> tuple:
        """ Immutable containers have a light color. """
        return 96, 64, 64

    set = None


class MutableContainer(Container):

    def color(self) -> tuple:
        """ Mutable containers are the default color of black. """
        return 0, 0, 0

    def set(self, key, value) -> None:
        """ A container only has this method if it is mutable. """
        raise NotImplementedError


class for_type:
    """ Decorator for classes that access items in a container of a specific data type. """

    _TABLE = []  # Data types and their corresponding containers.

    def __init__(self, tp:type):
        self.tp = tp

    def __lt__(self, other) -> bool:
        """ Sort classes by ancestry: child -> parent -> grandparent -> ... -> object. """
        return issubclass(self.tp, other.tp)

    def __call__(self, cls:type) -> type:
        """ Add each container under its type. Make sure subtypes are tested before base types. """
        self._TABLE.append((self, cls))
        self._TABLE.sort()
        return cls

    @classmethod
    def get_children(cls, obj) -> List[Container]:
        """ Return the first container in order that matches the object type, if any. """
        return next(([c(obj)] for t, c in cls._TABLE if isinstance(obj, t.tp)), [])


class for_attr(str):
    """ Decorator for classes that access items in a container held on a specific attribute. """

    _TABLE = []  # Data attributes and their corresponding containers.

    def __call__(self, cls:type) -> type:
        """ Add each container under its attribute. """
        self._TABLE.append((self, cls))
        return cls

    @classmethod
    def get_children(cls, obj) -> List[Container]:
        """ Return each container in order that matches the object type, if any. """
        return [c(obj) for a, c in cls._TABLE if hasattr(obj, a)]


@for_type(Iterable)
class ItemContainer(Container):
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

    def __iter__(self) -> Iterator[tuple]:
        """ For iterables such as sequences, automatically generate index numbers as the keys. """
        return enumerate(iter(self._obj))


@for_type(MutableSequence)
class MutableItemContainer(ItemContainer, MutableContainer):

    def set(self, key, value) -> None:
        """ Set a container item by index/key. """
        self._obj[key] = value


@for_type(Mapping)
class MappingContainer(ItemContainer):

    def __iter__(self) -> Iterator[tuple]:
        """ A mapping is shown in purest form with keys and values. """
        return iter(self._obj.items())


@for_type(MutableMapping)
class MutableMappingContainer(MappingContainer, MutableItemContainer):
    pass


@for_type(AbstractSet)
class SetContainer(ItemContainer):

    def __iter__(self) -> Iterator[tuple]:
        """ Sets behave mostly like sequences but are unordered. Use the hashes as indices to avoid confusion. """
        return zip(map(hash, self._obj), self._obj)


@for_type(MutableSet)
class MutableSetContainer(SetContainer, MutableContainer):

    def set(self, key, value) -> None:
        """ The keys are hashes, so iterate through the items and replace the item with that hash. """
        for hs, item in self:
            if hs == key:
                self._obj.remove(item)
                self._obj.add(value)
                return


@for_attr("__dict__")
class AttrContainer(MutableContainer):

    def __len__(self) -> int:
        return len(self._obj.__dict__)

    def __iter__(self) -> Iterator[tuple]:
        """ Include an entry for the class (unless the object *is* a class) along with the instance attributes. """
        tp = type(self._obj)
        if tp is not type and hasattr(tp, "__dict__"):
            yield ("__class__", tp)
        yield from self._obj.__dict__.items()

    def set(self, key, value) -> None:
        """ setattr will fail on attributes such as data descriptors, but so will modifying __dict__ directly. """
        setattr(self._obj, key, value)
