from functools import partial
from io import TextIOWrapper
from reprlib import Repr
from typing import Iterable, Iterator, List, Tuple

from .container import Container, for_attr, for_type
from spectra_lexer.utils import memoize

# Data types to treat as atomic (base types only). Do not look for children; display them as strings only.
_ATOMIC_TYPES = {type(None), bool, int, float, str, classmethod, staticmethod, type(lambda: None), TextIOWrapper}


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
        self.maxother = 50
        self.maxstring = 100

    def repr_instance(self, obj:object, level:int) -> str:
        """ Simpler version of reprlib.repr for arbitrary objects that doesn't cut out in the middle. """
        try:
            s = repr(obj)
        except Exception:
            s = None
        if s is None or len(s) > self.maxother:
            return '<%s object at %#x>' % (obj.__class__.__name__, id(obj))
        return s


value_repr = NodeRepr().repr


class ContainerCollection(Iterable[List[dict]]):
    """ Creates "containers" which handle the iterable contents or attributes of an object. """

    _seq: Iterable[Container] = ()

    def __init__(self, obj:object):
        """ Determine the right container types based on an object's type and/or attributes and make a list of them. """
        self._tp = type(obj)
        if self._tp in _ATOMIC_TYPES:
            return
        self._seq = for_type.get_children(obj) + for_attr.get_children(obj)

    def __bool__(self) -> bool:
        return any(self._seq)

    def __str__(self) -> str:
        return " - ".join([self._tp.__name__, *filter(None, map(str, self._seq))])

    def __iter__(self) -> Iterator[List[dict]]:
        for c in self._seq:
            edit_cb = c.set
            color = c.color()
            for key, obj in c:
                tp = type(obj)
                children = ContainerCollection(obj)
                # Column 0: the primary tree item with the key. Only it has an icon; possible icons are based on type.
                yield [{"color": color, "text": str(key), "icon_choices": mro_names(tp),
                        "has_children": bool(children), "child_data": children},
                       # Column 1: contains the type of object and/or item count. Has a tooltip detailing the MRO.
                       {"color": color, "text": str(children), "tooltip": mro_tree(tp)},
                       # Column 2: contains the string value of the object. The value may be edited if mutable.
                       {"color": color, "text": value_repr(obj), "edit": edit_cb and partial(edit_cb, key)}]
