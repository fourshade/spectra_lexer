from functools import partial
from reprlib import Repr
from typing import Iterator, List, Tuple

from .collection import ContainerCollection
from spectra_lexer.utils import memoize


@memoize
def mro_names(tp:type) -> Tuple[str]:
    """ Compute and cache a tuple of name strings for a type's MRO. """
    return (*[cls.__name__ for cls in tp.__mro__],)


@memoize
def mro_tree(tp:type) -> str:
    """ Compute and cache a string representation of a type's MRO. """
    return "\n".join([("--" * i) + name for i, name in enumerate(mro_names(tp)[::-1])])


class NodeRepr(Repr):
    """ Special repr utility for displaying values of various Python objects in a node tree. """

    def __init__(self):
        super().__init__()
        self.maxlevel = 2
        self.maxother = 100
        self.maxstring = 100

    def repr_instance(self, obj:object, level:int) -> str:
        """ Simpler version of reprlib.repr for arbitrary objects that doesn't cut out in the middle. """
        try:
            s = repr(obj)
            if len(s) <= self.maxother:
                return s
        except Exception:
            pass
        return f'<{obj.__class__.__name__} object at 0x{id(obj):0>8X}>'


value_repr = NodeRepr().repr


class Container:
    """ A container of child objects in some manner, such as iterable contents or attributes. """

    color = (96, 64, 64)  # Immutable containers have a light color.
    edit_tooltip = "Immutable structure; cannot edit."

    def __init__(self, obj):
        self._obj = obj

    # Determines the expandibility of items. Don't allow expansion by default.
    __len__ = int
    # If not empty, will be added to the type string of the base object. Return an empty string by default.
    __str__ = str

    # Return a string display value for the key. Does not actually have to be related, but is str(key) by default.
    key_str = str

    def kv_pairs(self) -> Iterator[tuple]:
        """ Whatever contents we have, they must be keyed in some way to return (k, v) tuples.
            Keep in mind that there could be thousands of items, or it could even be an infinite iterator.
            To be safe, return a lazy iterator so the program only evaluates items up to the child limit.
            For iterables with no other context, generate sequential index numbers for the keys. """
        return enumerate(self._obj)

    def edit_callback(self, key):
        """ Return None for immutable data types. This disables the editing of fields in the GUI. """
        return None

    def __iter__(self) -> Iterator[List[dict]]:
        """ From the object's keyed contents, yield one list of dicts for each item. """
        # These properties apply to all items in a container.
        base = dict(color=self.color)
        edit_tooltip = self.edit_tooltip
        for k, obj in self.kv_pairs():
            tp = type(obj)
            children = ContainerCollection(obj)
            # There are three columns, each starting out with the base data.
            # Column 0: the primary tree item with the key. Only it has an icon; possible icons are based on type.
            key_col = dict(base, text=self.key_str(k), icon_choices=mro_names(tp),
                           has_children=bool(children), child_data=children)
            # Column 1: contains the type of object and/or item count. Has a tooltip detailing the MRO.
            type_col = dict(base, text=children.type_str, tooltip=mro_tree(tp))
            # Column 2: contains the string value of the object. The value may be edited if mutable.
            val_col = dict(base, text=value_repr(obj), tooltip=edit_tooltip, edit=self.edit_callback(k))
            yield [key_col, type_col, val_col]


class MutableContainer(Container):

    color = (0, 0, 0)  # Mutable containers are the default color of black.
    edit_tooltip = "Double-click to edit this value."

    def edit_callback(self, key):
        """ Return a callback to replace the object under <key> with a user value. """
        return partial(self.setitem, key)

    def setitem(self, key, value) -> None:
        """ A container only has this method if it is mutable. Defaults to the behavior of __setitem__. """
        self._obj[key] = value
