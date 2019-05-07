from collections import defaultdict
from reprlib import Repr
from typing import Tuple

from spectra_lexer.utils import memoize


@memoize
def mro_names(tp:type) -> Tuple[str]:
    """ Compute and cache a tuple of name strings for a type's MRO. """
    return (*[cls.__name__ for cls in tp.__mro__],)


@memoize
def mro_tree(tp:type) -> str:
    """ Compute and cache a string representation of a type's MRO. """
    levels = defaultdict(int)
    for cls in tp.__mro__[::-1]:
        levels[cls] = max([levels[b] for b in cls.__bases__], default=-1) + 1
    return "\n".join([("--" * i) + cls.__name__ for cls, i in levels.items()])


class ItemRepr(Repr):
    """ Special repr utility for displaying values and types of various Python objects in a node tree. """

    def __init__(self):
        super().__init__()
        self.maxlevel = 2
        self.maxother = 100
        self.maxstring = 100

    def repr_instance(self, obj:object, level:int) -> str:
        """ Simpler version of reprlib.repr for arbitrary objects that doesn't cut out in the middle. """
        try:
            s = repr(obj)
            if len(s) <= self.maxother and s != object.__repr__(obj):
                return s
        except Exception:
            pass
        return f'<{obj.__class__.__name__} object at 0x{id(obj):0>8X}>'

    def add_key_data(self, d:dict, obj) -> None:
        """ Only column 0 has an icon; possible icons are based on type. """
        d["icon_choices"] = mro_names(type(obj))

    def add_type_data(self, d:dict, obj) -> None:
        """ Column 1 has a tooltip detailing the MRO. """
        d["text"] = type(obj).__name__
        d["tooltip"] = mro_tree(type(obj))

    def add_value_data(self, d:dict, obj) -> None:
        """ Column 2: contains the string value of the object. """
        d["text"] = self.repr(obj)
