from reprlib import Repr
from typing import Iterable, Iterator, List, Tuple

from .collection import ContainerCollection
from spectra_lexer.utils import delegate_to, memoize


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
            if len(s) <= self.maxother and s != object.__repr__(obj):
                return s
        except Exception:
            pass
        return f'<{obj.__class__.__name__} object at 0x{id(obj):0>8X}>'


class Container(Iterable[List[dict]]):
    """ A container of child objects in some manner, such as iterable contents or attributes. """

    _VALUE_REPR = NodeRepr().repr  # Custom repr class to compute string representations of values.

    color: tuple = (96, 64, 64)  # Immutable containers have a light color.
    key_tooltip: str = "Immutable structure; cannot edit."
    value_tooltip: str = key_tooltip

    def __init__(self, obj):
        self._obj = obj

    # Determines the expandability of items. Don't allow expansion by default.
    __bool__ = bool
    # If not empty, will be added to the type string of the base object. Return an empty string by default.
    __str__ = str
    # Return a string display value for the key. Does not actually have to be related, but is str(key) by default.
    key_str = str

    def __iter__(self) -> Iterator[List[dict]]:
        """ From the object's keyed contents, yield one list of dicts for each item. """
        try:
            for key in self.keys():
                yield self.item_data(key)
        except Exception as e:
            # Unpredictable exceptions may arise during introspection, so just present an error for any one.
            yield from ErroredContainer(e)

    def keys(self) -> Iterator:
        """ Whatever contents we have, they must be keyed in some way.
            Keep in mind that there could be thousands of items, or it could even be an infinite iterator.
            To be safe, return a lazy iterator so the program only evaluates items up to the child limit.
            For iterables with no other context, only the objects themselves can be the keys. """
        return iter(self._obj)

    def item_data(self, key) -> List[dict]:
        """ There are three columns, each starting out with the base data and adding specific column data. """
        obj = self[key]
        tp = type(obj)
        children = ContainerCollection(obj)
        base = self.base_data()
        return [{**base, **fn(key, obj, tp, children)} for fn in (self.key_data, self.type_data, self.value_data)]

    def base_data(self) -> dict:
        """ Return the base data that applies to all items in all columns. """
        return {"color": self.color}

    def key_data(self, key, obj, tp:type, children:ContainerCollection) -> dict:
        """ Column 0: the primary tree item with the key. Only it has an icon; possible icons are based on type. """
        d = {"text": self.key_str(key), "tooltip": self.key_tooltip, "icon_choices": mro_names(tp)}
        if children:
            d["has_children"] = True
            d["child_data"] = children
        return d

    def type_data(self, key, obj, tp:type, children:ContainerCollection) -> dict:
        """ Column 1: contains the type of object and/or item count. Has a tooltip detailing the MRO. """
        type_str = tp.__name__
        count_str = str(children)
        if count_str:
            type_str += " - " + count_str
        return {"text": type_str, "tooltip": mro_tree(tp)}

    def value_data(self, key, obj, tp:type, children:ContainerCollection) -> dict:
        """ Column 2: contains the string value of the object. The value may be edited if mutable. """
        return {"text": self._VALUE_REPR(obj), "tooltip": self.value_tooltip}

    # Most containers can be indexed. Ones that can't must have an alternate way to find items by key.
    __getitem__ = delegate_to("_obj")


def _add_edit_callback(d, fn, *args, cb_key="edit", eval_input=False) -> dict:
    """ Add a callback for editing of GUI fields to a dict. """
    def edit(user_input:str) -> bool:
        """ Attempt an edit operation and abort on any exception. Return True on success. """
        try:
            # Since only strings can be entered, we may evaluate them as Python expressions.
            if eval_input:
                user_input = eval_string(user_input)
            fn(*args, user_input)
            return True
        except Exception:
            # If the value was not a valid Python expression or editing failed another way, do nothing.
            return False
    d[cb_key] = edit
    return d


def eval_string(s:str):
    """ Evaluate a user string as a Python expression. If there's an undefined name, try to import its module. """
    d = globals()
    while True:
        try:
            return eval(s, d)
        except NameError as e:
            name = e.args[0].split("'")[1]
            d[name] = __import__(name)


class MutableContainer(Container):

    color = (0, 0, 0)  # Mutable containers are the default color of black.
    key_tooltip = "This key may not be changed."
    value_tooltip = "Double-click to edit this value."

    def value_data(self, key, *args) -> dict:
        """ Include a callback for editing of values in the data dict. """
        return _add_edit_callback(super().value_data(key, *args), self.__setitem__, key, eval_input=True)

    # A container only has these methods if it is mutable.
    __delitem__ = delegate_to("_obj")
    __setitem__ = delegate_to("_obj")


class MutableKeyContainer(MutableContainer):

    key_tooltip = "Double-click to move this item to another key."

    def key_data(self, key, *args) -> dict:
        """ Include a callback for editing of keys in the data dict. """
        return _add_edit_callback(super().key_data(key, *args), self.moveitem, key)

    def moveitem(self, old_key, new_key:str) -> None:
        """ A container only has this method if it is mutable AND it makes sense to change an item's order/key. """
        self[new_key] = self[old_key]
        del self[old_key]


class ErroredContainer(Container):

    color = (192, 0, 0)  # Errors are bright red.
    key_tooltip = value_tooltip = "An unexpected error occurred."

    def key_str(self, key):
        return "ERROR"

    def __iter__(self) -> Iterator[List[dict]]:
        """ Yield the exception's data if possible. Further exception handling is futile. """
        try:
            yield self.item_data(self._obj)
        except Exception:
            pass

    def __getitem__(self, key):
        return self._obj
