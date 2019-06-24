from functools import partial
from typing import Callable, Iterator, List, Mapping

from spectra_lexer.types.importer import AutoImporter


class Container(Mapping):
    """ A container of child objects in some manner, such as iterable contents or attributes.
        Whatever contents we have, they must be keyed in some way to satisfy the mapping protocol.
        Most containers can be subscripted. Ones that can't must have an alternate way to find items by key.
        For iterables with no other context, only the objects themselves can be the keys. """

    color: tuple = (96, 64, 64)  # Immutable containers have a light color.
    key_tooltip: str = "Immutable structure; cannot edit."
    value_tooltip: str = key_tooltip
    show_item_count: bool = False  # If True, len of items will be added to the type string of the base object.

    def __init__(self, obj):
        self._obj = obj

    def __iter__(self) -> Iterator:
        """ Keep in mind that there could be thousands of items, or there could even be an infinite iterator.
            To be safe, only use lazy iterators so the program can stop evaluation at a defined limit. """
        return iter(self._obj)

    def __len__(self) -> int:
        return len(self._obj)

    def __getitem__(self, key):
        return self._obj[key]

    def contents(self) -> Iterator:
        for key in self:
            yield (self[key], self._key_data(key), self._type_data(key), self._value_data(key))

    def _key_data(self, key) -> dict:
        """ Use str(key) by default for the key display value. """
        return {"color": self.color, "tooltip": self.key_tooltip, "text": str(key)}

    def _type_data(self, key) -> dict:
        return {"color": self.color}

    def _value_data(self, key) -> dict:
        return {"color": self.color, "tooltip": self.value_tooltip}


class MutableContainer(Container):

    color = (0, 0, 0)  # Mutable containers are the default color of black.
    key_tooltip = "This key may not be changed."
    value_tooltip = "Double-click to edit this value."

    # A container only has these methods if it is mutable.
    def __delitem__(self, key) -> None:
        del self._obj[key]

    def __setitem__(self, key, value) -> None:
        self._obj[key] = value

    def _value_data(self, key) -> dict:
        """ Include a callback for editing of values in the data dict with Python expressions. """
        d = super()._value_data(key)
        d["edit"] = EvalEditCallback(self.__setitem__, key)
        return d


class MutableKeyContainer(MutableContainer):

    key_tooltip = "Double-click to move this item to another key."

    def moveitem(self, old_key, new_key:str) -> None:
        """ A container only has this method if it is mutable AND it makes sense to change an item's order/key. """
        self[new_key] = self[old_key]
        del self[old_key]

    def _key_data(self, key) -> dict:
        """ Include a callback for editing of string keys in the data dict. """
        d = super()._key_data(key)
        d["edit"] = EditCallback(self.moveitem, key)
        return d


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


class ContainerIndex:
    """ Decorator for container classes that attempt to match some property of an object.
        The object provided as the key for .matches is always the first argument to a comparison function.
        Each recorded decorator has a property that is tested against this object as the second argument.
        If the comparison is True, that container class will be instantiated and may add items to the tree. """

    _INDICES: list = []

    _classes: list  # List of registered container classes.
    _cmp: Callable  # A binary comparison function that returns True/False.

    def __init__(self, cmp:Callable):
        self._classes = []
        self._cmp = cmp
        self._INDICES.append(self)

    def __call__(self, prop:object) -> Callable:
        """ Record a container subtype by the property to be compared. """
        def recorder(tp:type) -> type:
            self._classes.append((prop, tp))
            return tp
        return recorder

    def matches(self, obj:object) -> List[Container]:
        """ Get a list of registered container classes that compare True against the object's properties. """
        return [tp for prop, tp in self._classes if self._cmp(obj, prop)]

    @classmethod
    def match_all(cls, obj:object) -> List[Container]:
        """ Get container classes from each index that match the object's properties and instantiate them.
            If any classes from the same index are in a direct inheritance line, only keep the most derived class. """
        containers = []
        for index in cls._INDICES:
            matches = index.matches(obj)
            containers += [tp(obj) for tp in matches if sum([issubclass(m, tp) for m in matches]) == 1]
        return containers


if_hasattr = ContainerIndex(hasattr)
if_isinstance = ContainerIndex(isinstance)
