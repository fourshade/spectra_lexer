from io import TextIOWrapper
from typing import Iterable, Iterator

from .container import BaseContainer, CONTAINER_TYPES
from .data import DebugData


class DataFactory:
    """ Generates data for displaying the properties and contents of a Python object.
        generate() can create a data item directly from an object. The root item *must* be created this way.
        __iter__  will generate items from a series of "containers" stored in the instance. """

    # Base data types to treat as atomic/indivisible. Attempting iteration on these is either wasteful or harmful.
    _ATOMIC_TYPES = {type(None), type(...),      # System singletons.
                     bool, int, float, complex,  # Guaranteed not iterable.
                     str, bytes, bytearray,      # Items are just characters; do not iterate over these.
                     range, slice,               # Items are just a pre-determined mathematical range.
                     filter, map, zip,           # Iteration is destructive.
                     TextIOWrapper}              # Iteration may crash the program if std streams are in use.

    def __init__(self, containers:Iterable[BaseContainer]=()) -> None:
        self._containers = containers  # Containers from which to generate more child data objects.

    @classmethod
    def generate(cls, obj:object) -> DebugData:
        """ Create a root data object from scratch. """
        data = DebugData()
        cls.populate(obj, data)
        return data

    @classmethod
    def populate(cls, obj:object, data:DebugData) -> None:
        """ Gather parameters from the object's type, value, and possible contents. Add these parameters to <data>. """
        data.add_params(obj)
        # Only allow container expansion for types where it is useful.
        # Expanding strings into a row for each character is a mess just waiting to happen.
        # (especially since each character is *also* a string...containing itself.)
        if type(obj) in cls._ATOMIC_TYPES:
            return
        # Use the container type registry to make containers which match the object's properties.
        containers = CONTAINER_TYPES.match(obj)
        if containers:
            # If containers exist, make a new factory with them to handle generating children.
            if any(containers):
                data.child_data = cls(containers)
            item_counts = [len(c) for c in containers if c.show_item_count]
            if item_counts:
                data.item_count = sum(item_counts)

    def __iter__(self) -> Iterator[DebugData]:
        """ Create and yield data items from each container in turn. """
        for container in self._containers:
            try:
                for k in container:
                    data = DebugData()
                    obj = container[k]
                    container.set_data(k, data)
                    self.populate(obj, data)
                    yield data
            except Exception as e:
                # Unpredictable exceptions may arise during introspection, so just present an error for any one.
                data = self.generate(e)
                data.key_text = "ERROR"
                yield data
