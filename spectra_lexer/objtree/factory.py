from functools import partial
from typing import Any, Callable, Iterable, Iterator, Tuple, Collection

from .container import BaseContainer, CONTAINER_TYPES
from .format import SVGIconData, SVGIcons, TypeParams, ValueRepr


class ObjectData:
    """ A structure used to fully describe an object for debug purposes. """

    color: Tuple[int, int, int] = (0, 0, 0)
    key_text: str = "undefined"
    key_tooltip: str = ""
    key_edit: Callable = None
    type_text: str = "undefined"
    type_graph: str = ""
    item_count: int = None
    value_text: str = "undefined"
    value_tooltip: str = ""
    value_edit: Callable = None
    icon_data: SVGIconData = None
    children: Collection["ObjectData"] = ()

    def add_parent_data(self, container:BaseContainer, k:Any) -> None:
        """ Add all parent container data. This data has the lowest override priority. """
        if "color" not in vars(self):
            self.color = container.color
        self.key_tooltip = container.key_tooltip
        self.key_text = container.key_str(k)
        self.value_tooltip = container.value_tooltip
        if container.key_edit is not None:
            self.key_edit = partial(container.key_edit, k)
        if container.value_edit is not None:
            self.value_edit = partial(container.value_edit, k)


class ObjectDataFactory(Collection[ObjectData]):
    """ Generates data for displaying the properties and contents of a Python object. """

    _value_repr = ValueRepr().repr  # Generates strings representing an object's value.

    def __init__(self, icons=SVGIcons(), containers:Iterable[BaseContainer]=()) -> None:
        self._icons = icons            # Index of XML icons by data type.
        self._containers = containers  # Containers from which to generate more child data objects.

    def __bool__(self) -> bool:
        return any(self._containers)

    def __contains__(self, x:object) -> bool:
        return False

    def __len__(self) -> int:
        return sum(map(len, self._containers))

    def __iter__(self) -> Iterator[ObjectData]:
        """ Create and yield data items from each container in turn. """
        for container in self._containers:
            try:
                for k in container:
                    obj = container[k]
                    data = self.generate(obj)
                    data.add_parent_data(container, k)
                    yield data
            except Exception as e:
                # Unpredictable exceptions may arise during introspection, so just present an error for any one.
                data = self.generate(e)
                data.key_text = "ERROR"
                yield data

    def generate(self, obj:object) -> ObjectData:
        """ Create a new debug data object from properties of <obj>. """
        data = ObjectData()
        type_params = TypeParams(type(obj))
        is_metacls = isinstance(obj, type) and issubclass(obj, type)
        # Add data related to an object's type.
        data.type_text = type_params.name
        data.type_graph = type_params.graph
        # Exceptions are bright red in any container.
        if type_params.is_exc:
            data.color = (192, 0, 0)
        data.icon_data = self._icons.get_best(type_params, is_metacls)
        data.value_text = self._value_repr(obj)
        # Use the container type registry to make containers which match the object's properties.
        containers = CONTAINER_TYPES.match(obj)
        if containers:
            # If containers exist, make a new factory with them to handle generating children.
            data.children = self.__class__(self._icons, containers)
            item_counts = [len(c) for c in containers if c.show_item_count]
            if item_counts:
                data.item_count = sum(item_counts)
        return data
