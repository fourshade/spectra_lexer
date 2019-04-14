""" Module for container classes that access items held on a specific attribute. """

import builtins
import types
from typing import Iterator

from .collection import use_if
from .container import Container, MutableKeyContainer


@use_if(hasattr, "__class__")
class ClassContainer(Container):

    color = (32, 32, 128)  # Class containers are blue.
    _EXCLUDED_CLASSES: set = {i for m in (builtins, types) for i in vars(m).values() if isinstance(i, type)}

    def __bool__(self) -> bool:
        """ Allow class access if the object has an instance dict. Metaclasses may be accessed as well.
            The main exception is type, which is its own class and would expand indefinitely.
            Others include built-in types which provide next to nothing useful in their attr listings. """
        return hasattr(self._obj, "__dict__") and self._obj.__class__ not in self._EXCLUDED_CLASSES

    def keys(self) -> Iterator[str]:
        """ If allowed, yield the class alone, keyed by its name. """
        if self:
            yield self._obj.__class__.__name__

    def __getitem__(self, key:str) -> None:
        tp = self._obj.__class__
        if self and key == tp.__name__:
            return tp
        raise KeyError(tp)


@use_if(hasattr, "__dict__")
class AttrContainer(MutableKeyContainer):

    key_tooltip: str = "Double-click to change this attribute name."
    value_tooltip: str = "Double-click to edit this attribute."

    def __bool__(self) -> int:
        return bool(self._obj.__dict__)

    def keys(self) -> Iterator[str]:
        """ Include all instance attributes. """
        return iter(self._obj.__dict__)

    def __contains__(self, key:str) -> bool:
        """ Return True if there is an attribute under <key>. """
        return hasattr(self._obj, key)

    def __getitem__(self, key:str):
        """ Return the attribute under <key> by any method we can. """
        try:
            return getattr(self._obj, key)
        except AttributeError:
            return self._obj.__dict__[key]

    def __delitem__(self, key:str) -> None:
        """ Delete the attribute under <key> if it exists. """
        if key in self:
            delattr(self._obj, key)

    def __setitem__(self, key:str, value) -> None:
        """ __dict__ may be a mappingproxy, so setattr is the best way to set attributes.
            Deleting the attribute before setting the new value may help to override data descriptors. """
        del self[key]
        setattr(self._obj, key, value)
