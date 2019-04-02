from functools import partial
from itertools import islice

from .container import Container, MutableContainer
from .repr import NodeRepr

# Custom repr object for displaying node values.
VALUE_REPR = NodeRepr().repr
# Default maximum number of child nodes to generate.
CHILD_LIMIT = 200


class Node:
    """ Node containing info about an arbitrary Python object and callbacks to display it in a GUI tree. """

    def __init__(self, obj:object, key:object="ROOT", parent:Container=None):
        """ Create a new node. It may have attributes or container contents that can expand into child nodes. """
        children = Container.from_type(obj)
        self.icon_id = type_name = type(obj).__name__
        self.key_str = str(key)
        self.type_str = " - ".join(filter(None, map(str, [type_name, *children])))
        self.value_str = VALUE_REPR(obj)
        self.expand = partial(_expand, children) if any(children) else None
        self.edit = partial(_edit, parent, key) if isinstance(parent, MutableContainer) else None


def _expand(containers:list) -> list:
    """ Return a node for each object in the given containers. """
    return [Node(v, k, c) for c in containers for k, v in islice(c, CHILD_LIMIT)]


def _edit(container:MutableContainer, key:object, value:str) -> Node:
    """ Replace the value at a given key in a container. Return a replacement node if successful. """
    try:
        # Since only strings can be entered, we must evaluate them as Python expressions.
        # Any exception is possible; just abort if one occurs.
        obj = eval(value)
        return Node(obj, container.set(key, obj), container)
    except Exception:
        pass
