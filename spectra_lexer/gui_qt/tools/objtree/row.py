""" Module for formatting and displaying types and values of arbitrary Python objects. """

from collections import defaultdict
from functools import lru_cache
from io import TextIOWrapper

from .container import ContainerData
from .repr import ValueRepr


@lru_cache(maxsize=None)
def _mro_names(tp:type) -> tuple:
    """ Compute and cache a tuple of name strings for a type's MRO. """
    return (*[cls.__name__ for cls in tp.__mro__],)


@lru_cache(maxsize=None)
def _mro_tree(tp:type) -> str:
    """ Compute and cache a string representation of a type's MRO. """
    levels = defaultdict(int)
    for cls in tp.__mro__[::-1]:
        levels[cls] = max([levels[b] for b in cls.__bases__], default=-1) + 1
    return "\n".join([("--" * i) + cls.__name__ for cls, i in levels.items()])


class RowData(dict):
    """ A tree row consisting of three items. """

    # Base data types to treat as atomic/indivisible. Attempting iteration on these is either wasteful or harmful.
    _ATOMIC_TYPES: set = {type(None), type(...),      # System singletons.
                          bool, int, float, complex,  # Guaranteed not iterable.
                          str, bytes, bytearray,      # Items are just characters; do not iterate over these.
                          range, slice,               # Results of iteration are completely pre-determined.
                          filter, map, zip,           # Iteration is destructive.
                          TextIOWrapper}              # Iteration may crash the program if std streams are in use.

    def __init__(self, obj:object, data:dict=()):
        super().__init__(data)
        self._add_object_data(obj)

    def _add_object_data(self, obj:object) -> None:
        """ Exceptions are bright red. """
        tp = type(obj)
        if issubclass(tp, BaseException):
            self["color"] = (192, 0, 0)
        self["icon_choices"] = _mro_names(tp)
        self["type_text"] = tp.__name__
        self["type_tooltip"] = _mro_tree(tp)
        self["value_text"] = ValueRepr().repr(obj)
        if tp not in self._ATOMIC_TYPES:
            self.update(ContainerData(obj, self.__class__))
