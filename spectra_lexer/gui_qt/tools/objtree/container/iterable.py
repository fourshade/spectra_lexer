""" Module for container classes that access items specific to an iterable data type. """

from typing import AbstractSet, Iterator, Mapping, MutableMapping, MutableSequence, MutableSet, Sequence

from .base import Container, if_isinstance, MutableContainer, MutableKeyContainer


@if_isinstance(Mapping)
class UnorderedContainer(Container):
    """ A sized, unordered iterable item container. The most generic acceptable type of iterable container.
        Items may be sorted for display if they are orderable. Mappings do not need a subclass beyond this. """

    _AUTOSORT_MAXSIZE: int = 200
    show_item_count = True

    def __iter__(self) -> Iterator:
        """ If the container is under a certain size, attempt to sort its objects by key.
            A sort operation may fail if some keys aren't comparable. """
        if len(self) < self._AUTOSORT_MAXSIZE:
            try:
                return iter(sorted(self._obj))
            except TypeError:
                pass
        return iter(self._obj)


@if_isinstance(MutableMapping)
class MutableMappingContainer(UnorderedContainer, MutableKeyContainer):
    """ The base container classes are already implemented as mappings. No changes need to be made. """


@if_isinstance(AbstractSet)
class SetContainer(UnorderedContainer):

    key_tooltip = "Hash value of the object. Cannot be edited."

    def __getitem__(self, key):
        """ The key is the item itself. """
        if key in self._obj:
            return key
        raise KeyError(key)

    def _key_str(self, key) -> str:
        """ Since the items are both the keys and the values, display hashes in the key field. """
        return f"#{hash(key)}"


@if_isinstance(MutableSet)
class MutableSetContainer(SetContainer, MutableContainer):

    def __delitem__(self, key) -> None:
        """ The key is the old item itself. Remove it. """
        self._obj.discard(key)

    def __setitem__(self, key, value) -> None:
        """ The key is the old item itself. Remove it and add the new item. """
        del self[key]
        self._obj.add(value)


@if_isinstance(Sequence)
class SequenceContainer(Container):

    show_item_count = True

    def __iter__(self) -> Iterator[int]:
        """ Generate sequential index numbers as the keys. """
        return iter(range(len(self._obj)))

    def _key_str(self, key:int) -> str:
        """ Add a dot in front of each index for clarity. """
        return f".{key}"


@if_isinstance(tuple)
class TupleContainer(SequenceContainer):

    def _key_str(self, key:int) -> str:
        """ By default, namedtuples display as regular tuples. Show them with their named fields instead. """
        if hasattr(self._obj, "_fields"):
            return f".{key} - {self._obj._fields[key]}"
        return super()._key_str(key)


@if_isinstance(MutableSequence)
class MutableSequenceContainer(SequenceContainer, MutableKeyContainer):

    key_tooltip = "Double-click to move this item to a new index (non-negative integers only)."

    def moveitem(self, old_key:int, new_key:str) -> None:
        """ Moving a sequence item from one index to another can be done, but it will shift every item in between. """
        k = int(new_key)
        self[k:k] = [self[old_key]]
        del self[old_key + (old_key >= k)]
