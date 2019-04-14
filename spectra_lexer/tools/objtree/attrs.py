import builtins
import types
from typing import Iterator

from .collection import for_property
from .container import Container, MutableContainer


class for_attr(for_property):
    """ Decorator for classes that access items in a container held on a specific attribute. """

    def __init__(self, attr:type):
        self.attr = attr

    @classmethod
    def get_children(cls, obj) -> list:
        """ Return each container in order whose attribute is possessed by the object. """
        return [c(obj) for self, c in cls.PROP_TABLE if hasattr(obj, self.attr)]


@for_attr("__class__")
class ClassContainer(Container):

    color = (32, 32, 128)  # Class containers are blue.
    _EXCLUDED_CLASSES: set = {i for m in (builtins, types) for i in vars(m).values() if isinstance(i, type)}

    def __len__(self) -> int:
        """ Allow class access if the object has an instance dict. Metaclasses may be accessed as well.
            The main exception is type, which is its own class and would expand indefinitely.
            Others include built-in types which provide next to nothing useful in their attr listings. """
        return hasattr(self._obj, "__dict__") and self._obj.__class__ not in self._EXCLUDED_CLASSES

    def kv_pairs(self) -> Iterator[tuple]:
        """ If allowed, yield the class alone, keyed by its name. """
        if self:
            tp = self._obj.__class__
            yield (tp.__name__, tp)


@for_attr("__dict__")
class AttrContainer(MutableContainer):

    def __len__(self) -> int:
        return len(self._obj.__dict__)

    def kv_pairs(self) -> Iterator[tuple]:
        """ Include all instance attributes. """
        return iter(self._obj.__dict__.items())

    def setitem(self, key, value) -> None:
        """ setattr will fail on attributes such as data descriptors, but so will modifying __dict__ directly. """
        setattr(self._obj, key, value)
