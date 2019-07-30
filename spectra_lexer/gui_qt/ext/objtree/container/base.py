from functools import partial
from typing import Callable, Iterator, List, Mapping

from spectra_lexer.utils import AutoImporter


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

    def item_data(self) -> Iterator:
        """ Yield all objects and data associated with this container. """
        for k in self:
            yield self[k], self._data(k)

    def _data(self, key) -> dict:
        """ Add all base data and any additional data from subclasses. """
        return {"color": self.color, "key_tooltip": self.key_tooltip,
                "key_text": self._key_str(key), "value_tooltip": self.value_tooltip}

    # Use str(key) by default for the key display value.
    _key_str = str


class MutableContainer(Container):

    _EVAL_NAMESPACE: dict = None

    color = (0, 0, 0)  # Mutable containers are the default color of black.
    key_tooltip = "This key may not be changed."
    value_tooltip = "Double-click to edit this value."

    # A container only has these methods if it is mutable.
    def __delitem__(self, key) -> None:
        del self._obj[key]

    def __setitem__(self, key, value) -> None:
        self._obj[key] = value

    def _data(self, key) -> dict:
        """ Include a callback for editing of values in the data dict with Python expressions. """
        data = super()._data(key)
        data["value_edit"] = partial(self.eval_setitem, key)
        return data

    def eval_setitem(self, key, user_input:str) -> None:
        """ Since only strings can be entered, we must evaluate them as Python expressions.
            ast.literal_eval is safer, but not quite as useful (or fun). No need for restraint here. """
        try:
            self[key] = eval(user_input, self._get_namespace())
        except Exception as e:
            # User input + eval = BREAK ALL THE THINGS!!! At least try to replace the item with the exception.
            self[key] = e

    @classmethod
    def _get_namespace(cls) -> dict:
        """ Since there's no interpreter prompt, the system can try to import missing modules automatically.
            Creating the autoimport dict is expensive, so don't do it until we actually have to evaluate something. """
        if cls._EVAL_NAMESPACE is None:
            cls._EVAL_NAMESPACE = AutoImporter.make_namespace()
        return cls._EVAL_NAMESPACE


class MutableKeyContainer(MutableContainer):

    key_tooltip = "Double-click to move this item to another key."

    def moveitem(self, old_key, new_key:str) -> None:
        """ A container only has this method if it is mutable AND it makes sense to change an item's order/key. """
        self[new_key] = self[old_key]
        del self[old_key]

    def _data(self, key) -> dict:
        """ Include a callback for editing of string keys in the data dict. """
        data = super()._data(key)
        data["key_edit"] = partial(self.moveitem, key)
        return data


class ContainerIter:

    _containers: List[Container]
    _factory: Callable

    def __init__(self, containers, factory):
        self._containers = containers
        self._factory = factory

    def __iter__(self) -> Iterator:
        """ Create and yield rows from each container in turn. """
        for container in self._containers:
            try:
                for obj, data in container.item_data():
                    yield self._factory(obj, data)
            except Exception as e:
                # Unpredictable exceptions may arise during introspection, so just present an error for any one.
                yield self._factory(e, {"key_text": "ERROR"})


class ContainerData(dict):
    """ Handles data for all containers that display the contents of an object. """

    _INDICES: list = []

    def __init__(self, obj, factory:Callable):
        super().__init__()
        classes = self._match_classes(obj)
        containers = [cls(obj) for cls in _filter_classes(classes)]
        if containers:
            if any(containers):
                self["child_data"] = ContainerIter(containers, factory)
            item_counts = [len(c) for c in containers if c.show_item_count]
            if item_counts:
                self["item_count"] = sum(item_counts)

    @classmethod
    def index(cls, cmp:Callable) -> Callable:
        """ Decorator for container classes that attempt to match some property of an object.
            The object provided as the key for .matches is always the first argument to a comparison function.
            Each recorded decorator has a property that is tested against this object as the second argument.
            If the comparison is True, that container class will be instantiated and may add items to the tree. """
        def deco(prop:object) -> Callable:
            def record(tp:type) -> type:
                cls._INDICES.append((cmp, prop, tp))
                return tp
            return record
        return deco

    @classmethod
    def _match_classes(cls, obj:object) -> List[type]:
        """ Get container classes from each index that match the object's properties. """
        return [tp for cmp, prop, tp in cls._INDICES if cmp(obj, prop)]


def _filter_classes(matches:List[type]) -> List[type]:
    """ If any container classes are in a direct inheritance line, only keep the most derived class. """
    return [tp for tp in matches if sum([issubclass(m, tp) for m in matches]) == 1]


if_hasattr = ContainerData.index(hasattr)
if_isinstance = ContainerData.index(isinstance)
