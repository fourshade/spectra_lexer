import builtins
from io import TextIOWrapper
from itertools import islice
from typing import Iterable, Mapping, MutableMapping, MutableSequence, MutableSet

from .container import AttrContainer, ItemContainer, MappingContainer, MutableContainer, MutableMappingContainer, \
    MutableSetContainer
from .repr import NodeRepr

# Custom repr object for displaying node values.
REPR = NodeRepr()
# Default maximum number of child nodes to generate.
CHILD_LIMIT = 200
# Data types to treat as atomic (base types only). Do not look for children; display them as strings only.
_ATOMIC_TYPES = {type(None), bool, int, float, str, classmethod, staticmethod, type(lambda: None), TextIOWrapper}
# Data types and their corresponding containers.
# Mutability matters; only classes with a "set" method will be editable.
_TYPE_TABLE = {MutableSequence: MutableContainer,
               MutableMapping: MutableMappingContainer,
               Mapping: MappingContainer,
               MutableSet: MutableSetContainer,
               Iterable: ItemContainer}


class NodeData:
    """ Node containing an arbitrary Python object and the information needed to display it in a GUI tree.
        It may have child objects which are attributes or container contents. """

    def __init__(self, key, obj, parent=None):
        self._key = key
        self._parent = parent
        self._containers = []
        self._add_containers(obj)
        self._type_str = " - ".join(filter(None, map(str, [type(obj).__name__, *self._containers])))
        self._value_str = REPR.repr(obj)

    def __len__(self) -> int:
        """ Return the number of items in every container combined. """
        return sum(map(len, self._containers))

    def info(self) -> tuple:
        """ Return a list of display info for this node, including name, type, and value. """
        return str(self._key), self._type_str, self._value_str

    def is_editable(self) -> bool:
        return hasattr(self._parent, "set")

    def children(self) -> list:
        """ Return a list of child nodes for this object if it has any. """
        return [NodeData(k, v, c) for c in self._containers for k, v in islice(c, CHILD_LIMIT)]

    def set_value(self, value:str):
        """ Replace a node's value on its parent from a value string. Return its replacement node if successful. """
        try:
            # Since only strings can be entered, we must evaluate them as Python expressions.
            # Any exception is possible; just abort if one occurs.
            obj = eval(value)
            c = self._parent
            return NodeData(c.set(self._key, obj), obj, c)
        except Exception:
            return None

    def _add_containers(self, obj) -> None:
        """ Determine the right container types based on the object's type and add them. """
        if type(obj) not in _ATOMIC_TYPES:
            for t, c in _TYPE_TABLE.items():
                if isinstance(obj, t):
                    self._containers.append(c(obj))
                    break
            if hasattr(obj, "__dict__"):
                self._containers.append(AttrContainer(obj))
