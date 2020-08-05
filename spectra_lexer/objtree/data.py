from functools import partial
from typing import Callable, Collection, Iterator, Sequence

from .container import BaseContainer, ContainerRegistry, MutableContainer, MovableKeyContainer
from .icons import SVGIconData, SVGIconFinder


class ObjectData:
    """ Data structure used to fully describe an object for debug purposes. """

    color = (0, 0, 0)                        # RGB 0-255 color tuple for all object display text.
    key_text = "undefined"                   # Main display text for object's container key.
    key_tooltip = ""                         # Popup tooltip for object's container key.
    type_text = "undefined"                  # Main display text for object's data type.
    type_graph = ""                          # Graph display text for MRO of object's data type
    value_text = "undefined"                 # Main display text for object (its string value).
    value_tooltip = ""                       # Popup tooltip for object's value.
    op_edit: Callable[[str], None] = None    # Callback to replace the object with the results of eval() on a string.
    op_delete: Callable[[], None] = None     # Callback to delete the object from its container.
    op_move: Callable[[str], None] = None    # Callback to move the object to a new key in its container.
    icon_data: SVGIconData = None            # Bytes data for the object's SVG icon (may be None)
    children: Collection["ObjectData"] = ()  # Iterable collection of child data objects.
    item_count: int = None                   # Displayed count of children in the object (None if not displayed).


class ObjectDataFactory:
    """ Generates data for displaying the properties and contents of a Python object. """

    def __init__(self, matcher:ContainerRegistry, mro_grapher:Callable[[type], str], value_repr:Callable[[object], str],
                 icon_finder=SVGIconFinder(), eval_ns:dict=None, exc_color=(192, 0, 0)) -> None:
        self._matcher = matcher          # Matches objects to containers that can find their contents.
        self._mro_grapher = mro_grapher  # Generates strings representing a graph of an object type's MRO.
        self._value_repr = value_repr    # Generates strings representing an object's value.
        self._icon_finder = icon_finder  # Index of SVG XML icons by data type.
        self._eval_ns = eval_ns          # Namespace for evaluation of user input strings as Python code.
        self._exc_color = exc_color      # Exceptions are always bright red, overriding any color due to containers.

    def generate(self, obj:object) -> ObjectData:
        """ Create a root data object from properties of <obj>. """
        data = ObjectData()
        self._add_value(data, obj)
        return data

    def generate_child(self, container:BaseContainer, k:object) -> ObjectData:
        """ Create a data object from the child of <container> under key <k>. """
        data = ObjectData()
        data.color = container.color
        data.key_text = container.key_str(k)
        data.key_tooltip = container.key_tooltip
        data.value_tooltip = container.value_tooltip
        if isinstance(container, MutableContainer):
            data.op_edit = partial(self._eval_setitem, container, k)
            data.op_delete = partial(container.__delitem__, k)
            if isinstance(container, MovableKeyContainer):
                # Only allow movement using literal string input for now.
                data.op_move = partial(container.moveitem, k)
        self._add_value(data, container[k])
        return data

    def _eval_setitem(self, container:MutableContainer, k:object, user_input:str) -> None:
        """ Since only strings can be entered by a user, we must evaluate them as Python expressions.
            ast.literal_eval is safer, but not quite as useful (or fun). No need for restraint here. """
        try:
            container[k] = eval(user_input, self._eval_ns)
        except Exception as e:
            # User input + eval = BREAK ALL THE THINGS!!! At least try to replace the item with the exception.
            container[k] = e

    def generate_error(self, exc:Exception) -> ObjectData:
        """ Create a data object from an internal <exc>eption. """
        data = self.generate(exc)
        data.key_text = "ERROR"
        data.key_tooltip = data.value_tooltip = "Internal error."
        data.value_text = "Cannot analyze object."
        return data

    def _add_value(self, data:ObjectData, obj:object) -> None:
        """ Add data related to an object's type and value. """
        tp = type(obj)
        if issubclass(tp, BaseException):
            data.color = self._exc_color
        data.type_text = tp.__name__
        data.type_graph = self._mro_grapher(tp)
        data.value_text = self._value_repr(obj)
        data.icon_data = self._icon_finder.get_best(obj)
        # If containers exist, add a new collection with them to handle generating children.
        containers = self._matcher.containers_from(obj)
        if containers:
            data.children = ObjectDataChildren(self, containers)
            item_counts = [len(c) for c in containers if c.show_item_count]
            if item_counts:
                data.item_count = sum(item_counts)


class ObjectDataChildren:
    """ Lazy iterable ObjectData generator. Implements the full collection protocol. """

    def __init__(self, factory:ObjectDataFactory=None, containers:Sequence[BaseContainer]=()) -> None:
        self._factory = factory        # Base factory for data objects.
        self._containers = containers  # Containers from which to generate more child data objects.
        self._cache = {}               # Cache for previously created data items.

    def __bool__(self) -> bool:
        """ Return True if any single container has contents. """
        return any(self._containers)

    def __contains__(self, data:object) -> bool:
        """ Return True if <data> was created by our iterator. Efficiency is poor. """
        return data in self._cache.values()

    def __len__(self) -> int:
        """ Return the size of all containers combined. """
        return sum(map(len, self._containers))

    def __iter__(self) -> Iterator[ObjectData]:
        """ Create and yield data items from each container in turn.
            Store new ones in a cache for repeat iteration and __contains__. """
        cache = self._cache
        factory = self._factory
        for container in self._containers:
            try:
                for k, obj in container.items():
                    ck = id(k), id(obj)
                    if ck not in cache:
                        cache[ck] = factory.generate_child(container, k)
                    yield cache[ck]
            except Exception as e:
                # Unpredictable exceptions may arise when parsing data from arbitrary objects.
                # If this happens, yield a special data item from the exception and move to the next container.
                yield factory.generate_error(e)
