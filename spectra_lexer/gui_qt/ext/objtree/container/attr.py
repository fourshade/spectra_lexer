""" Module for container classes that access items held on a specific attribute. """

from typing import Iterator

from .base import if_hasattr, MutableKeyContainer


@if_hasattr("__dict__")
class AttrContainer(MutableKeyContainer):

    key_tooltip: str = "Double-click to change this attribute name."
    value_tooltip: str = "Double-click to edit this attribute value."

    def __iter__(self) -> Iterator:
        return iter(vars(self._obj))

    def __len__(self) -> int:
        return len(vars(self._obj))

    def __getitem__(self, key:str):
        """ Return the attribute under <key> by any method we can. """
        try:
            return vars(self._obj)[key]
        except KeyError:
            return getattr(self._obj, key)

    def __delitem__(self, key:str) -> None:
        """ Delete the attribute under <key> if it exists. """
        if hasattr(self._obj, key):
            delattr(self._obj, key)

    def __setitem__(self, key:str, value) -> None:
        """ __dict__ may be a mappingproxy, so setattr is the best way to set attributes.
            Deleting the attribute before setting the new value may help to override data descriptors. """
        del self[key]
        setattr(self._obj, key, value)
