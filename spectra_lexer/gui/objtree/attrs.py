""" Module for container classes that access items held on a specific attribute. """

import builtins
import types
from typing import Iterator

from .collection import use_if
from .container import Container, MutableKeyContainer
from spectra_lexer.types import delegate_to


@use_if(hasattr, "__class__")
class ClassContainer(Container):

    color = (32, 32, 128)  # Class containers are blue.
    key_tooltip = value_tooltip = "Auto-generated item; cannot edit."
    _EXCLUDED_CLASSES: set = {i for m in (builtins, types) for i in vars(m).values() if isinstance(i, type)}

    _cls_dict = {}  # Pre-computed class hierarchy dict by name.

    def __init__(self, obj):
        """ Allow class access if the object has an instance dict. Metaclasses may be accessed as well.
            The main exception is type, which is its own class and would expand indefinitely.
            Others include built-in types which provide next to nothing useful in their attr listings. """
        super().__init__(obj)
        if hasattr(obj, "__dict__"):
            self._cls_dict = {tp.__name__: tp for tp in obj.__class__.__mro__ if tp not in self._EXCLUDED_CLASSES}

    __bool__ = delegate_to("_cls_dict")

    def keys(self) -> Iterator[str]:
        return iter(self._cls_dict)

    __getitem__ = delegate_to("_cls_dict")


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
        except (AttributeError, TypeError):
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
