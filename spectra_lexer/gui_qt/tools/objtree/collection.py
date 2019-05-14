from io import TextIOWrapper
from typing import Iterable, Iterator, List

from .container import Container, ErroredContainer
from .item import ItemProps
from spectra_lexer.types import polymorph_index

# These decorate container classes. Each corresponds to a binary comparison function that returns True/False.
# The object under introspection is the first argument. The key given in the decorator is the second argument.
# If the comparison is True, the container class is instantiated and may provide items for that object in the tree.
use_if_object_is = polymorph_index()
_ISINSTANCE_INDEX = use_if_object_is.items()
use_if_object_has_attr = polymorph_index()
_HASATTR_INDEX = use_if_object_has_attr.items()


# Base data types to treat as atomic/indivisible. Attempting iteration on these is either wasteful or harmful.
ATOMIC_TYPES: set = {type(None), type(...),  # System singletons.
                     bool, int, float,       # Guaranteed not iterable.
                     str, bytes, bytearray,  # Items are just characters; do not iterate over these.
                     range, slice,           # Results of iteration are completely pre-determined by constants.
                     TextIOWrapper}          # Iteration may crash the program if std streams are in use.


class ContainerCollection(Iterable[List[dict]]):
    """ Handles "containers" that work with a particular property an object may have to inspect its contents. """

    _containers: List[Container] = []

    def __init__(self, obj:object):
        """ Get a list of containers from each independent container class that matches the object's properties.
            If any classes are in a direct inheritance line, only keep the most derived class. """
        if type(obj) not in ATOMIC_TYPES:
            matches = [tp for prop, tp in _ISINSTANCE_INDEX if isinstance(obj, prop)]
            matches += [tp for prop, tp in _HASATTR_INDEX if hasattr(obj, prop)]
            self._containers = [tp(obj) for tp in matches if sum([issubclass(m, tp) for m in matches]) == 1]

    def add_key_data(self, d:dict) -> None:
        """ The collection has items if any container does. """
        if any(self._containers):
            d["has_children"] = True
            d["child_data"] = self

    def add_type_data(self, d:dict) -> None:
        """ If any containers want to display their item count, display it next to the type info label. """
        if "text" in d:
            d["text"] += "".join([c.type_str() for c in self._containers])

    def add_value_data(self, d:dict) -> None:
        pass

    def __iter__(self) -> Iterator[List[dict]]:
        """ Yield items from each container in turn, adding the properties of the container and object. """
        for c in self._containers:
            try:
                base_data = c.base_data()
                for k, obj in c.items():
                    item_props = ItemProps(obj)
                    children = ContainerCollection(obj)
                    key_data, type_data, value_data = data = [d.copy() for d in base_data]
                    c.add_key_data(key_data, k)
                    item_props.add_key_data(key_data)
                    children.add_key_data(key_data)
                    c.add_type_data(type_data, k)
                    item_props.add_type_data(type_data)
                    children.add_type_data(type_data)
                    c.add_value_data(value_data, k)
                    item_props.add_value_data(value_data)
                    children.add_value_data(value_data)
                    yield data
            except Exception as e:
                # Unpredictable exceptions may arise during introspection, so just present an error for any one.
                yield from ErroredContainer(e)
