from io import TextIOWrapper
from itertools import islice
import reprlib
from typing import Iterable, Mapping, MutableMapping, MutableSequence, MutableSet

REPR = reprlib.Repr()
REPR.maxlevel = 2
REPR.maxstring = 100

# Default maximum number of child nodes to generate.
CHILD_LIMIT = 200


class NodeData:
    """ Node containing an arbitrary Python object and the information needed to display it in a GUI tree.
        It may have child objects which are attributes or container contents. By default, they have none. """

    def __init__(self, key, obj, parent=None):
        self._key = key
        self._parent = parent
        self._containers = _get_containers(obj)
        self._type_str = " - ".join(filter(None, map(str, [type(obj).__name__, *self._containers])))
        self._value_str = REPR.repr(obj)

    def info(self) -> tuple:
        """ Return a list of display info for this node, including name, type, value, editability, and children. """
        return str(self._key), self._type_str, self._value_str, hasattr(self._parent, "set"), self.children()

    def children(self) -> list:
        """ Return a list of child nodes for this object if it has any. """
        return [NodeData(k, v, c) for c in self._containers for k, v in islice(c, CHILD_LIMIT)]

    def set_value(self, value:str):
        """ Replace a node's value on its parent from a value string. Return its replacement node if successful. """
        try:
            # Since only strings can be entered, we must evaluate them as Python expressions.
            # Any exception is possible; just abort if one occurs.
            obj = eval(value)
            c = self._parent
            return NodeData(c.set(self._key, obj), obj, c)
        except Exception:
            return None


class ChildContainer:
    """ A container of child objects in some manner, such as iterable contents or attributes. """

    def __init__(self, obj):
        self._obj = obj

    def __str__(self) -> str:
        return ""

    def __iter__(self) -> Iterable[tuple]:
        """ Whatever contents we have, they must be keyed in some way to return (k, v) tuples.
            Keep in mind that there could be thousands of items, or it could even be an infinite iterator.
            To be safe, return a lazy iterator so the program only evaluates items up to the child limit. """
        raise NotImplementedError


class ItemContainer:
    """ An iterable item container. """

    def __init__(self, obj):
        self._obj = obj

    def __str__(self) -> str:
        """ Add the number of items to the type field if countable. """
        try:
            n = len(self._obj)
            return f"{n} item" + "s" * (n != 1)
        except TypeError:
            return ""

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


class AttrContainer(ChildContainer):

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


# Data types to treat as atomic (base types only). Do not look for children; display them as strings only.
_ATOMIC_TYPES = {type(None), bool, int, float, str, classmethod, staticmethod, type(NodeData.__init__), TextIOWrapper}
# Data types and their corresponding containers.
# Mutability matters; only classes with a "set" method will be editable.
_TYPE_TABLE = {MutableSequence: MutableContainer,
               MutableMapping:  MutableMappingContainer,
               Mapping:         MappingContainer,
               MutableSet:      MutableSetContainer,
               Iterable:        ItemContainer}


def _get_containers(obj):
    """ Determine the right container type based on the object's type. """
    tp = type(obj)
    containers = []
    if tp not in _ATOMIC_TYPES:
        for t, c in _TYPE_TABLE.items():
            if issubclass(tp, t):
                containers.append(c(obj))
                break
        if hasattr(obj, "__dict__"):
            containers.append(AttrContainer(obj))
    return containers
