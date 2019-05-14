from collections import defaultdict
from typing import Tuple

from .repr import ValueRepr
from spectra_lexer.utils import memoize


@memoize
def _mro_names(tp:type) -> Tuple[str]:
    """ Compute and cache a tuple of name strings for a type's MRO. """
    return (*[cls.__name__ for cls in tp.__mro__],)


@memoize
def _mro_tree(tp:type) -> str:
    """ Compute and cache a string representation of a type's MRO. """
    levels = defaultdict(int)
    for cls in tp.__mro__[::-1]:
        levels[cls] = max([levels[b] for b in cls.__bases__], default=-1) + 1
    return "\n".join([("--" * i) + cls.__name__ for cls, i in levels.items()])


class ItemProps:

    _VALUE_REPR = ValueRepr()

    color: tuple = None

    def __init__(self, obj:object):
        """ Exceptions are bright red. """
        self._obj = obj
        if isinstance(obj, Exception):
            self.color = (192, 0, 0)

    def add_key_data(self, d:dict) -> None:
        """ Only column 0 has an icon; possible icons are based on type. """
        self._add_color(d)
        d["icon_choices"] = _mro_names(type(self._obj))

    def add_type_data(self, d:dict) -> None:
        """ Column 1 has a tooltip detailing the MRO. """
        self._add_color(d)
        tp = type(self._obj)
        d["text"] = tp.__name__
        d["tooltip"] = _mro_tree(tp)

    def add_value_data(self, d:dict) -> None:
        """ Column 2: contains the string value of the object. """
        self._add_color(d)
        d["text"] = self._VALUE_REPR(self._obj)

    def _add_color(self, d:dict) -> None:
        color = self.color
        if color is not None:
            d["color"] = color
