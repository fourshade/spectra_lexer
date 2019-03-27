from itertools import islice
from typing import Mapping, Sequence

# Default maximum number of child items to generate
CHILD_LIMIT = 100
# Data types to parse as one unit (i.e. display them as strings instead of looking for children)
_UNIT_TYPES = (bool, int, float, str)


class NodeData:
    """ Node containing an arbitrary Python object and the information needed to display it in a GUI tree.
        It may have child objects which are attributes or container contents.
        The children should only be created or updated when needed. """

    def __init__(self, name:str, value, parent=None):
        self._name = name
        self._value = value
        self.parent = parent

    def fields(self) -> tuple:
        """ Return a list of display fields for this node, including name, type, and a string value or children. """
        value = self._value
        child_iter = _find_contents(value)
        # Show the object's item count if it has children and its value string if it doesn't.
        children = []
        if child_iter is not None:
            children = [NodeData(str(k), v, self) for k, v in islice(child_iter, CHILD_LIMIT)]
            count = getattr(value, "__len__", int)() or len(children)
            value_field = f"{count} items"
        if not children:
            value_field = str(value)
        return self._name, type(value).__name__, value_field, children

    def set_value(self, key:str, child_value) -> str:
        """ Set the value of a child from a key and value produced by fields.
            If the change was successful, return the new value in string form, otherwise return None. """
        return ""


def _find_contents(value):
    """ Determine what the contents of an object are based on the object's type.
        Note that we can't look inside arbitrary iterables because they might be consumable."""
    if value is None or isinstance(value, _UNIT_TYPES):
        # Unit types may or may not have contents, but we don't want to list each item i.e. in a string.
        return None
    elif isinstance(value, Mapping):
        # A mapping is shown in purest form with keys and values.
        return value.items()
    elif isinstance(value, Sequence):
        # A sequence has auto-generated indices as its display names.
        return enumerate(value)
    elif isinstance(value, (set, frozenset)):
        # Sets behave mostly like sequences but are unordered. Use the hashes as indices to avoid confusion.
        return zip(map(hash, value), value)
    elif hasattr(value, "__dict__"):
        # As a last resort, look for non-dunder attributes in the instance dict.
        items = [(k, v) for k, v in value.__dict__.items() if not k.startswith("__")]
        if items:
            return items
