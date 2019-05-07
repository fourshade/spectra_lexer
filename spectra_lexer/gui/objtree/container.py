from typing import Callable, Iterator, List, Mapping

from spectra_lexer.types import delegate_to


class Container(Mapping):
    """ A container of child objects in some manner, such as iterable contents or attributes.
        Whatever contents we have, they must be keyed in some way.
        Keep in mind that there could be thousands of items, or there could even be an infinite iterator.
        To be safe, return lazy iterators so the program only evaluates items up to the child limit.
        For iterables with no other context, only the objects themselves can be the keys.
        Most containers can be indexed. Ones that can't must have an alternate way to find items by key. """

    color: tuple = (96, 64, 64)  # Immutable containers have a light color.
    key_tooltip: str = "Immutable structure; cannot edit."
    value_tooltip: str = key_tooltip

    def __init__(self, obj):
        self._obj = obj

    # Return a string display value for the key. Does not actually have to be related, but is str(key) by default.
    key_str = str
    # If not empty, will be added to the type string of the base object. Return an empty string by default.
    type_str = str

    def base_data(self) -> List[dict]:
        return [{"color": self.color, "tooltip": self.key_tooltip},
                {"color": self.color},
                {"color": self.color, "tooltip": self.value_tooltip}]

    def add_key_data(self, d:dict, key) -> None:
        """ Column 0: the primary tree item with the key. """
        d["text"] = self.key_str(key)

    def add_type_data(self, d:dict, key) -> None:
        """ Column 1: contains the type of object and/or item count. """
        pass

    def add_value_data(self, d:dict, key) -> None:
        """ Column 2: contains the value of the object. It may be edited if mutable. """
        pass


def _edit_callback(fn, key, eval_input=False) -> Callable:
    """ Make a callback for editing of GUI fields to a dict. """
    def edit(user_input:str) -> bool:
        """ Attempt an edit operation and abort on any exception. Return True on success. """
        try:
            # Since only strings can be entered, we may evaluate them as Python expressions.
            if eval_input:
                user_input = _eval_string(user_input)
            fn(key, user_input)
            return True
        except Exception:
            # If the value was not a valid Python expression or editing failed another way, do nothing.
            return False
    return edit


def _eval_string(s:str):
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

    def add_value_data(self, d:dict, key) -> None:
        """ Include a callback for editing of values in the data dict. """
        super().add_value_data(d, key)
        d["edit"] = _edit_callback(self.__setitem__, key, eval_input=True)

    # A container only has these methods if it is mutable.
    __delitem__ = delegate_to("_obj")
    __setitem__ = delegate_to("_obj")


class MutableKeyContainer(MutableContainer):

    key_tooltip = "Double-click to move this item to another key."

    def add_key_data(self, d:dict, key) -> None:
        """ Include a callback for editing of keys in the data dict. """
        super().add_key_data(d, key)
        d["edit"] = _edit_callback(self.moveitem, key)

    def moveitem(self, old_key, new_key:str) -> None:
        """ A container only has this method if it is mutable AND it makes sense to change an item's order/key. """
        self[new_key] = self[old_key]
        del self[old_key]


class ErroredContainer(Container):

    color = (192, 0, 0)  # Errors are bright red.
    key_tooltip = value_tooltip = "An unexpected error occurred."

    def __len__(self) -> int:
        return 1

    def __iter__(self) -> Iterator:
        yield "ERROR"

    def __getitem__(self, key):
        """ Show the exception's data if possible. Further exception handling is futile. """
        return self._obj
