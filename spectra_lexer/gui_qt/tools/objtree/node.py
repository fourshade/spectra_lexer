from itertools import islice
import reprlib
from typing import AbstractSet, Iterable, Mapping, MutableMapping, MutableSequence, MutableSet, Sequence

# Default maximum number of items to put in a value string.
VALUE_LIMIT = 10
# Default maximum number of child nodes to generate.
CHILD_LIMIT = 100


class NodeData:
    """ Node containing an arbitrary Python object and the information needed to display it in a GUI tree.
        It may have child objects which are attributes or container contents. By default, they have none.
        The children should only be created or updated when needed. """

    def __init__(self, key, obj, parent=None):
        self._key = key
        self._obj = obj
        self._parent = parent
        self.editable = bool(getattr(parent, "set_child", None))

    @classmethod
    def from_object(cls, key, obj:object, parent=None):
        """ Determine the node type for an object and make one. """
        return _get_node_type(obj)(key, obj, parent)

    def fields(self) -> tuple:
        """ Return a list of display fields for this node, including name, type, value, and children. """
        return str(self._key), self.type_str(), reprlib.repr(self._obj), self.children()

    def type_str(self) -> str:
        """ Return a string for the object that will go in the 'type' field of the table. """
        return type(self._obj).__name__

    def children(self) -> list:
        """ Return a list of child nodes for this object if it has any. """
        return []

    def set_value(self, value:str):
        """ Replace a node's value on its parent from a value string. Return its replacement node if successful. """
        if self.editable:
            try:
                # Since only strings can be entered, we must evaluate them as Python expressions.
                # Anything could happen there, so just abort on any exception.
                obj = eval(value)
                key = self._parent.set_child(self._key, obj)
                return NodeData.from_object(key, obj, self._parent)
            except Exception:
                return None
        return None


class ContainerNode(NodeData):

    def type_str(self) -> str:
        """ Add the number of items to the type field. """
        return super().type_str() + f" - {len(self._obj)} items"

    def children(self) -> Iterable:
        """ Create a node for each child, up to a predetermined limit. """
        return [NodeData.from_object(k, v, self) for k, v in islice(self.contents(), CHILD_LIMIT)]

    def contents(self) -> Iterable[tuple]:
        """ Whatever contents we have, they must be keyed in some way. """
        return []


class SequenceNode(ContainerNode):

    def contents(self) -> Iterable[tuple]:
        """ For sequences, automatically generate index numbers as the keys. """
        return enumerate(iter(self._obj))


class MutableSequenceNode(SequenceNode):

    def set_child(self, key, child):
        self._obj[key] = child
        return key


class MappingNode(ContainerNode):

    def contents(self) -> Iterable[tuple]:
        """ A mapping is shown in purest form with keys and values. """
        return self._obj.items()


class MutableMappingNode(MappingNode):

    set_child = MutableSequenceNode.set_child


class SetNode(ContainerNode):

    def contents(self) -> Iterable[tuple]:
        """ Sets behave mostly like sequences but are unordered. Use the hashes as indices to avoid confusion. """
        return zip(map(hash, self._obj), self._obj)


class MutableSetNode(SetNode):

    def set_child(self, key, child):
        for item in self._obj:
            if hash(item) == key:
                self._obj.remove(item)
                self._obj.add(child)
                break
        return hash(child)


class AttributeNode(ContainerNode):

    type_str = NodeData.type_str

    def contents(self) -> Iterable[tuple]:
        return [(k, v) for k, v in vars(self._obj).items() if not k.startswith("__")]

    def set_child(self, key, child):
        setattr(self._obj, key, child)
        return key


# Data types to parse as one unit (i.e. display them as strings instead of looking for children)
_UNIT_TYPES = (type(None), bool, int, float, str)
# Data types/tuples and their corresponding nodes. Mutability matters
_TYPE_TABLE = {_UNIT_TYPES:     NodeData,
               MutableSequence: MutableSequenceNode,
               Sequence:        SequenceNode,
               MutableMapping:  MutableMappingNode,
               Mapping:         MappingNode,
               MutableSet:      MutableSetNode,
               AbstractSet:     SetNode}


def _get_node_type(obj:object) -> type:
    """ Determine the right node type based on the object's type. """
    for t, n in _TYPE_TABLE.items():
        if isinstance(obj, t):
            return n
    # If all else fails, let the contents be non-dunder attributes in the instance dict.
    if hasattr(obj, "__dict__"):
        return AttributeNode
    return NodeData
