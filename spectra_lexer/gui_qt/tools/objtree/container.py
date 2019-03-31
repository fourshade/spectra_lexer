from typing import Iterable


class Container:
    """ A container of child objects in some manner, such as iterable contents or attributes. """

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

    def __iter__(self) -> Iterable[tuple]:
        """ For iterables such as sequences, automatically generate index numbers as the keys. """
        return enumerate(iter(self._obj))


class MutableContainer(ItemContainer):

    def set(self, key, child):
        """ A container only has this method if it is mutable. """
        self._obj[key] = child
        return key


class MappingContainer(ItemContainer):

    def __iter__(self) -> Iterable[tuple]:
        """ A mapping is shown in purest form with keys and values. """
        return iter(self._obj.items())


class MutableMappingContainer(MappingContainer, MutableContainer):
    pass


class SetContainer(ItemContainer):

    def __iter__(self) -> Iterable[tuple]:
        """ Sets behave mostly like sequences but are unordered. Use the hashes as indices to avoid confusion. """
        return zip(map(hash, self._obj), self._obj)


class MutableSetContainer(SetContainer):

    def set(self, key, child):
        """ The keys are hashes, so iterate through the items and replace the item with that hash. """
        for h, v in self:
            if h == key:
                self._obj.remove(v)
                self._obj.add(child)
                return hash(child)


class AttrContainer(Container):

    def __len__(self):
        return len(self._obj.__dict__)

    def __iter__(self) -> Iterable[tuple]:
        """ Include an entry for the class (unless the object *is* a class) along with the instance attributes. """
        tp = type(self._obj)
        if tp is not type and hasattr(tp, "__dict__"):
            yield ("__class__", tp)
        yield from self._obj.__dict__.items()

    def set(self, key, child):
        """ setattr will fail on attributes such as data descriptors, but so will modifying __dict__ directly. """
        setattr(self._obj, key, child)
        return key
