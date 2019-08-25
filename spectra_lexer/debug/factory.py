from io import TextIOWrapper
from typing import List, Callable, Iterator, Tuple

from . import generated, iterable
from .container import Container
from .data import DebugData


class ContainerIter:

    _containers: List[Container]
    _factory: Callable

    def __init__(self, containers:List[Container], factory:Callable) -> None:
        self._containers = containers
        self._factory = factory

    def __iter__(self) -> Iterator[DebugData]:
        """ Create and yield rows from each container in turn. """
        for container in self._containers:
            try:
                for k in container:
                    data = DebugData()
                    obj = container[k]
                    container.set_data(k, data)
                    yield self._factory(obj, data)
            except Exception as e:
                # Unpredictable exceptions may arise during introspection, so just present an error for any one.
                data = DebugData()
                data.key_text = "ERROR"
                yield self._factory(e, data)


class DataFactory:
    """ Handles data for all containers that display the contents of an object. """

    # Base data types to treat as atomic/indivisible. Attempting iteration on these is either wasteful or harmful.
    _ATOMIC_TYPES = {type(None), type(...),      # System singletons.
                     bool, int, float, complex,  # Guaranteed not iterable.
                     str, bytes, bytearray,      # Items are just characters; do not iterate over these.
                     range, slice,               # Items are just a pre-determined mathematical range.
                     filter, map, zip,           # Iteration is destructive.
                     TextIOWrapper}              # Iteration may crash the program if std streams are in use.

    _conditions: List[Tuple[type, Callable, object]]

    def __init__(self) -> None:
        """ Each container class has a condition which attempts to match some property of an object.
            The object provided as the key for .matches is always the first argument to a comparison function.
            Each recorded decorator has a property that is tested against this object as the second argument.
            If the comparison is True, that container class will be instantiated and may add items to the tree. """
        self._conditions = [*generated.CONDITIONS, *iterable.CONDITIONS]

    def generate(self, obj:object) -> DebugData:
        """ Return a root data object from scratch. """
        data = DebugData()
        return self.populate(obj, data)

    def populate(self, obj:object, data:DebugData) -> DebugData:
        """ Gather and add parameters from the object's type, value, and possible contents. """
        data.add_params(obj)
        # Only allow container expansion for types where it is useful.
        # Expanding strings into a row for each character is a mess just waiting to happen.
        # (especially since each character is *also* a string...containing itself.)
        if type(obj) in self._ATOMIC_TYPES:
            return data
        # Get container classes from each index that match the object's properties.
        # If any container classes are in a direct inheritance line, only keep the most derived class.
        classes = [tp for tp, cmp, prop in self._conditions if cmp(obj, prop)]
        containers = [tp(obj) for tp in classes if sum([issubclass(m, tp) for m in classes]) == 1]
        if containers:
            if any(containers):
                data.child_data = ContainerIter(containers, self.populate)
            item_counts = [len(c) for c in containers if c.show_item_count]
            if item_counts:
                data.item_count = sum(item_counts)
        return data
