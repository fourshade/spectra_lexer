""" Module for container classes that access items specific to a data type. """

from typing import AbstractSet, Collection, Iterator, Mapping, MutableMapping, MutableSequence, MutableSet, Sequence

from .collection import use_if
from .container import Container, MutableContainer, MutableKeyContainer
from spectra_lexer.utils import delegate_to


@use_if(isinstance, Collection)
class SizedContainer(Container):
    """ A sized iterable item container. The most generic acceptable type of iterable container. """

    __bool__ = delegate_to("_obj")
    __len__ = delegate_to("_obj")

    def __str__(self) -> str:
        """ Add the number of items to the type field. """
        n = len(self)
        return f"{n} item" + "s" * (n != 1)


@use_if(isinstance, AbstractSet)
class SetContainer(SizedContainer):

    key_tooltip: str = "Hash value of the object. Cannot be edited."

    def key_str(self, key) -> str:
        """ Sets behave mostly like sequences but are unordered. Display the hashes to avoid confusion. """
        return str(hash(key))

    def __getitem__(self, key):
        """ The key is the item itself. """
        if key in self._obj:
            return key
        raise KeyError(key)


@use_if(isinstance, MutableSet)
class MutableSetContainer(SetContainer, MutableContainer):

    def __delitem__(self, key) -> None:
        """ The key is the old item itself. Remove it. """
        self._obj.discard(key)

    def __setitem__(self, key, value) -> None:
        """ The key is the old item itself. Remove it and add the new item. """
        del self[key]
        self._obj.add(value)


@use_if(isinstance, Sequence)
class SequenceContainer(SizedContainer):

    def key_str(self, key:int) -> str:
        """ Add a dot in front of each index for clarity. """
        return f".{key}"

    def keys(self) -> Iterator:
        """ Generate sequential index numbers as the keys. """
        return iter(range(len(self)))


@use_if(isinstance, MutableSequence)
class MutableSequenceContainer(SequenceContainer, MutableKeyContainer):

    key_tooltip: str = "Double-click to move this item to another index (non-negative integers only)."

    def moveitem(self, old_key:int, new_key:str) -> None:
        """ Moving a sequence item from one index to another can be done, but it will affect every item before it. """
        k = int(new_key)
        self[k:k] = [self[old_key]]
        del self[old_key + (old_key >= k)]


@use_if(isinstance, Mapping)
class MappingContainer(SizedContainer):

    _AUTOSORT_MAXSIZE: int = 200

    def keys(self) -> Iterator:
        """ Mappings are shown with their natural keys and values. If under a certain size, attempt to sort it by key.
            A sort operation may fail if some keys aren't comparable. """
        if len(self) < self._AUTOSORT_MAXSIZE:
            try:
                return iter(sorted(self._obj))
            except TypeError:
                pass
        return iter(self._obj)


@use_if(isinstance, MutableMapping)
class MutableMappingContainer(MappingContainer, MutableKeyContainer):
    pass
