""" Module for container classes that access items specific to an iterable data type. """

from typing import AbstractSet, Any, Iterator, Mapping, MutableMapping, MutableSequence, MutableSet, Sequence

from .container import Container, MutableContainer, MutableKeyContainer


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


class MutableMappingContainer(UnorderedContainer, MutableKeyContainer):
    """ The base container classes are already implemented as mappings. No changes need to be made. """


class SetContainer(UnorderedContainer):

    key_tooltip = "Hash value of the object. Cannot be edited."

    def __getitem__(self, key) -> Any:
        """ The key is the item itself. """
        if key in self._obj:
            return key
        raise KeyError(key)

    def _key_str(self, key) -> str:
        """ Since the items are both the keys and the values, display hashes in the key field. """
        return f"#{hash(key)}"


class MutableSetContainer(SetContainer, MutableContainer):

    def __delitem__(self, key) -> None:
        """ The key is the old item itself. Remove it. """
        self._obj.discard(key)

    def __setitem__(self, key, value:Any) -> None:
        """ The key is the old item itself. Remove it and add the new item. """
        del self[key]
        self._obj.add(value)


class SequenceContainer(Container):

    show_item_count = True

    def __iter__(self) -> Iterator[int]:
        """ Generate sequential index numbers as the keys. """
        return iter(range(len(self._obj)))

    def _key_str(self, key:int) -> str:
        """ Add a dot in front of each index for clarity. """
        return f".{key}"


class TupleContainer(SequenceContainer):

    def _key_str(self, key:int) -> str:
        """ By default, namedtuples display as regular tuples. Show them with their named fields instead. """
        if hasattr(self._obj, "_fields"):
            return f".{key} - {self._obj._fields[key]}"
        return super()._key_str(key)


class MutableSequenceContainer(SequenceContainer, MutableKeyContainer):

    key_tooltip = "Double-click to move this item to a new index (non-negative integers only)."

    def moveitem(self, old_key:int, new_key:str) -> None:
        """ Moving a sequence item from one index to another can be done, but it will shift every item in between. """
        k = int(new_key)
        self[k:k] = [self[old_key]]
        del self[old_key + (old_key >= k)]


class AttrContainer(MutableKeyContainer):

    key_tooltip: str = "Double-click to change this attribute name."
    value_tooltip: str = "Double-click to edit this attribute value."

    def __iter__(self) -> Iterator:
        return iter(vars(self._obj))

    def __len__(self) -> int:
        return len(vars(self._obj))

    def __getitem__(self, key:str) -> Any:
        """ Return the attribute under <key> by any method we can. """
        try:
            return vars(self._obj)[key]
        except KeyError:
            return getattr(self._obj, key)

    def __delitem__(self, key:str) -> None:
        """ Delete the attribute under <key> if it exists. """
        if hasattr(self._obj, key):
            delattr(self._obj, key)

    def __setitem__(self, key:str, value:Any) -> None:
        """ __dict__ may be a mappingproxy, so setattr is the best way to set attributes.
            Deleting the attribute before setting the new value may help to override data descriptors. """
        del self[key]
        setattr(self._obj, key, value)


CONDITIONS = [(UnorderedContainer,       isinstance, Mapping),
              (MutableMappingContainer,  isinstance, MutableMapping),
              (SetContainer,             isinstance, AbstractSet),
              (MutableSetContainer,      isinstance, MutableSet),
              (SequenceContainer,        isinstance, Sequence),
              (TupleContainer,           isinstance, tuple),
              (MutableSequenceContainer, isinstance, MutableSequence),
              (AttrContainer,            hasattr,    "__dict__")]
