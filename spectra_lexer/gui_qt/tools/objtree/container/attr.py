""" Module for container classes that access items held on a specific attribute. """

from typing import Iterator

from .base import Container, if_hasattr, MutableKeyContainer


@if_hasattr("__slots__")
class AttrContainer(Container):

    _ATTR = "__slots__"

    # Slots are tricky to modify. Keep them as read-only for now.
    key_tooltip = value_tooltip = "Attributes are slots; cannot edit."

    def __init__(self, obj):
        """ The chosen attribute container object is saved for easy access. """
        super().__init__(obj)
        self._attrs = getattr(obj, self._ATTR)

    def __iter__(self) -> Iterator:
        return iter(self._attrs)

    def __len__(self) -> int:
        return len(self._attrs)

    def __getitem__(self, key:str):
        """ Return the attribute under <key> by any method we can. """
        try:
            return getattr(self._obj, key)
        except (AttributeError, TypeError):
            return self._attrs[key]


@if_hasattr("__dict__")
class DictAttrContainer(AttrContainer, MutableKeyContainer):

    _ATTR = "__dict__"

    key_tooltip: str = "Double-click to change this attribute name."
    value_tooltip: str = "Double-click to edit this attribute value."

    def __delitem__(self, key:str) -> None:
        """ Delete the attribute under <key> if it exists. """
        if hasattr(self._obj, key):
            delattr(self._obj, key)

    def __setitem__(self, key:str, value) -> None:
        """ __dict__ may be a mappingproxy, so setattr is the best way to set attributes.
            Deleting the attribute before setting the new value may help to override data descriptors. """
        del self[key]
        setattr(self._obj, key, value)
