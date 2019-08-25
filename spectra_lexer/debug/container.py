""" Module with base classes for container data providers. """

from functools import partial
from typing import Any, Iterator, Mapping

from .data import DebugData


class Container(Mapping):
    """ A container of child objects in some manner, such as iterable contents or attributes.
        Whatever contents we have, they must be keyed in some way to satisfy the mapping protocol.
        Most containers can be subscripted. Ones that can't must have an alternate way to find items by key.
        For iterables with no other context, only the objects themselves can be the keys. """

    color: tuple = (96, 64, 64)  # Immutable containers have a light color.
    key_tooltip: str = "Immutable structure; cannot edit."
    value_tooltip: str = key_tooltip
    show_item_count: bool = False  # If True, len of items will be added to the type string of the base object.

    _obj: Any

    def __init__(self, obj:Any) -> None:
        self._obj = obj

    def __iter__(self) -> Iterator:
        """ Some objects could have thousands of items or even iterate indefinitely.
            To be safe, only use lazy iterators so the program can stop evaluation at a defined limit. """
        return iter(self._obj)

    def __len__(self) -> int:
        return len(self._obj)

    def __getitem__(self, key) -> Any:
        return self._obj[key]

    def set_data(self, key, data:DebugData) -> None:
        """ Add all base container data for the given key. Override with any additional data from subclasses. """
        data.color = self.color
        data.key_tooltip = self.key_tooltip
        data.key_text = self._key_str(key)
        data.value_tooltip = self.value_tooltip

    # Use str(key) by default for the key display value.
    _key_str = str


class MutableContainer(Container):

    color = (0, 0, 0)  # Mutable containers are the default color of black.
    key_tooltip = "This key may not be changed."
    value_tooltip = "Double-click to edit this value."

    # A container only has these methods if it is mutable.
    def __delitem__(self, key) -> None:
        del self._obj[key]

    def __setitem__(self, key, value:Any) -> None:
        self._obj[key] = value

    def set_data(self, key, data:DebugData) -> None:
        """ Include a callback for editing of values in the data dict with Python expressions. """
        super().set_data(key, data)
        data.value_edit = partial(self.eval_setitem, key)

    def eval_setitem(self, key, user_input:str, *, eval_fn=eval) -> None:
        """ Since only strings can be entered, we must evaluate them as Python expressions.
            ast.literal_eval is safer, but not quite as useful (or fun). No need for restraint here. """
        try:
            self[key] = eval_fn(user_input)
        except Exception as e:
            # User input + eval = BREAK ALL THE THINGS!!! At least try to replace the item with the exception.
            self[key] = e


class MutableKeyContainer(MutableContainer):

    key_tooltip = "Double-click to move this item to another key."

    def moveitem(self, old_key, new_key:str) -> None:
        """ A container only has this method if it is mutable AND it makes sense to change an item's order/key. """
        self[new_key] = self[old_key]
        del self[old_key]

    def set_data(self, key, data:DebugData) -> None:
        """ Include a callback for editing of string keys in the data dict. """
        super().set_data(key, data)
        data.key_edit = partial(self.eval_moveitem, key)

    def eval_moveitem(self, key, user_input:str, eval_fn=eval) -> None:
        """ Only allow movement using literal string input for now. """
        self.moveitem(key, user_input)


class GeneratedContainer(Container):
    """ An immutable container that generates a dict and stores that instead of the original object. """

    color = (32, 32, 128)  # Auto-generated containers are blue.
    key_tooltip = value_tooltip = "Auto-generated item; cannot edit."

    def __init__(self, obj:Any) -> None:
        d = self._gen_dict(obj)
        super().__init__(d)

    def _gen_dict(self, obj:Any) -> dict:
        return {}
