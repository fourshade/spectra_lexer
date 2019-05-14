from functools import partial
from typing import Iterator, List, Mapping

from spectra_lexer.types import delegate_to
from spectra_lexer.types.importer import AutoImporter


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


class MutableContainer(Container):

    color = (0, 0, 0)  # Mutable containers are the default color of black.
    key_tooltip = "This key may not be changed."
    value_tooltip = "Double-click to edit this value."

    def add_value_data(self, d:dict, key) -> None:
        """ Include a callback for editing of values in the data dict with Python expressions. """
        super().add_value_data(d, key)
        d["edit"] = EvalEditCallback(self.__setitem__, key)

    # A container only has these methods if it is mutable.
    __delitem__ = delegate_to("_obj")
    __setitem__ = delegate_to("_obj")


class MutableKeyContainer(MutableContainer):

    key_tooltip = "Double-click to move this item to another key."

    def add_key_data(self, d:dict, key) -> None:
        """ Include a callback for editing of string keys in the data dict. """
        super().add_key_data(d, key)
        d["edit"] = EditCallback(self.moveitem, key)

    def moveitem(self, old_key, new_key:str) -> None:
        """ A container only has this method if it is mutable AND it makes sense to change an item's order/key. """
        self[new_key] = self[old_key]
        del self[old_key]


class ErroredContainer(Container):

    key_tooltip = value_tooltip = "An unexpected error occurred."

    def __len__(self) -> int:
        return 1

    def __iter__(self) -> Iterator:
        yield "ERROR"

    def __getitem__(self, key):
        """ Show the exception object if possible. Further exception handling is futile. """
        return self._obj


class EditCallback(partial):
    """ Callback to reflect GUI field edits back to the container object. """

    def __call__(self, user_input:object) -> bool:
        """ Attempt an edit operation and abort on any exception. Return True on success. """
        try:
            super().__call__(user_input)
            return True
        except Exception:
            # Non-standard container classes could raise anything. Just tell the GUI it didn't work.
            return False


class EvalEditCallback(EditCallback):
    """ Callback to evaluate GUI field edits as Python expressions. """

    _EVAL_NAMESPACE: dict = None

    def __call__(self, user_input:str) -> bool:
        """ Since only strings can be entered, we must evaluate them as Python expressions.
            ast.literal_eval is safer, but not quite as useful (or fun). No need for restraint here. """
        try:
            return super().__call__(eval(user_input, self._get_namespace()))
        except Exception as e:
            # User input + eval = BREAK ALL THE THINGS!!! At least try to replace the item with the exception.
            return super().__call__(e)

    @classmethod
    def _get_namespace(cls) -> dict:
        """ Since there's no interpreter prompt, the system can try to import missing modules automatically.
            Creating the autoimport dict is expensive, so don't do it until we actually have to evaluate something. """
        if cls._EVAL_NAMESPACE is None:
            cls._EVAL_NAMESPACE = AutoImporter.make_namespace()
        return cls._EVAL_NAMESPACE
