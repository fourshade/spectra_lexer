from functools import partial
from typing import Any, Callable, Iterable, Iterator, Tuple

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

    def __init__(self, factory:Callable[[object], "ObjectData"]) -> None:
        self._factory = factory  # Factory to create more debug data objects from Python objects.
        self._containers = ()    # Containers from which to generate more child data objects.

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

    def add_type_data(self, type_params:TypeParams) -> None:
        """ Add data related to an object's type. """
        self.type_text = type_params.name
        self.type_graph = type_params.graph
        # Exceptions are bright red in any container.
        if type_params.is_exc:
            self.color = (192, 0, 0)

    def add_value_data(self, value_repr:str, icon:SVGIconData=None) -> None:
        """ Add data related to an object's value. """
        self.value_text = value_repr
        self.icon_data = icon

    def add_child_data(self, containers:Iterable[BaseContainer]) -> None:
        # If containers exist, make a new factory with them to handle generating children.
        if containers:
            self._containers = containers
            item_counts = [len(c) for c in containers if c.show_item_count]
            if item_counts:
                self.item_count = sum(item_counts)

    def __bool__(self) -> bool:
        return any(self._containers)

    def __contains__(self, x:object) -> bool:
        return False

    def __len__(self) -> int:
        return sum(map(len, self._containers))

    def __iter__(self) -> Iterator["ObjectData"]:
        """ Create and yield data items from each container in turn. """
        for container in self._containers:
            try:
                for k in container:
                    data = self._factory(container[k])
                    data.add_parent_data(container, k)
                    yield data
            except Exception as e:
                # Unpredictable exceptions may arise during introspection, so just present an error for any one.
                data = self._factory(e)
                data.key_text = "ERROR"
                yield data


class ObjectDataFactory:
    """ Generates data for displaying the properties and contents of a Python object. """

    _value_repr = ValueRepr().repr  # Generates strings representing an object's value.

    def __init__(self, icons=SVGIcons()) -> None:
        self._icons = icons  # Index of XML icons by data type.

    def generate(self, obj:object) -> ObjectData:
        """ Create a new debug data object from properties of <obj>. """
        data = ObjectData(self.generate)
        type_params = TypeParams(type(obj))
        data.add_type_data(type_params)
        is_metacls = isinstance(obj, type) and issubclass(obj, type)
        icon = self._icons.get_best(type_params, is_metacls)
        val = self._value_repr(obj)
        data.add_value_data(val, icon)
        # Use the container type registry to make containers which match the object's properties.
        containers = CONTAINER_TYPES.match(obj)
        data.add_child_data(containers)
        return data
