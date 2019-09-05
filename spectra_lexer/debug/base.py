import csv
from functools import partial
import pkgutil
import sys
from typing import Any, Callable, Iterable, Iterator, Tuple

from .container import BaseContainer, CONTAINER_TYPES
from .format import TypeParams, ValueRepr


class package(dict):
    """ Dict for nesting objects and modules under path-like string keys. Has a special icon. """

    __slots__ = ()

    @classmethod
    def modules(cls):
        """ Make a package with a nested representation of the currently loaded modules. """
        return cls.nested(sys.modules, delim=".", root_key="__init__")

    @classmethod
    def nested(cls, src:dict, delim:str, root_key:str):
        """ Split all keys in <src> on <delim> and nest package dicts in a hierarchy based on these splits.
            If one key is a prefix of another, it may occupy a slot needed for another level of dicts.
            If this happens, move the value one level deeper under <root_key>. """
        pkg = cls()
        for k, v in src.items():
            d = pkg
            *first, last = k.split(delim)
            for i in first:
                if i not in d:
                    d[i] = cls()
                elif not isinstance(d[i], cls):
                    d[i] = cls({root_key: d[i]})
                d = d[i]
            if last not in d or not isinstance(d[last], cls):
                d[last] = v
            else:
                d[last][root_key] = v
        return pkg


class DebugData:
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
    icon_data: bytes = None

    _containers = ()  # Containers from which to generate more child data objects.

    def __init__(self, factory:Callable) -> None:
        self._factory = factory  # Factory to create more debug data objects from Python objects.

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

    def add_value_data(self, value_repr:str, icon:bytes=None) -> None:
        """ Add data related to an object's value. """
        self.value_text = value_repr
        self.icon_data = icon

    def add_child_data(self, containers:Iterable[BaseContainer]):
        # If containers exist, make a new factory with them to handle generating children.
        if containers:
            self._containers = containers
            item_counts = [len(c) for c in containers if c.show_item_count]
            if item_counts:
                self.item_count = sum(item_counts)

    def __bool__(self) -> bool:
        return any(self._containers)

    def __iter__(self) -> Iterator:
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


class DebugDataFactory:
    """ Generates data for displaying the properties and contents of a Python object.
        package() can create a data item directly from an object. The root item *must* be created this way.
        __iter__  will generate items from a series of "containers" stored in the instance. """

    ICON_PACKAGE = __package__    # Name of Python package containing the file with all object tree icons.
    ICON_PATH = "/treeicons.dat"  # Relative path to icon file.

    def __init__(self, root_package=ICON_PACKAGE.split(".")[0]) -> None:
        self._root_package = root_package    # Name of root Python package for components using the gear icon.
        self._icons = {}                     # Index of XML icon data keyed by the names of object data types.
        self._value_repr = ValueRepr().repr  # Generates strings representing an object's value

    def load_icons(self, package:str=ICON_PACKAGE, path:str=ICON_PATH) -> None:
        """ Parse the given icon resource as a CSV file. The first row contains only one field:
            the basic document structure with header and footer, usable as a format string.
            In all other rows, the last field is the SVG icon data itself, and every other field
            contains the name of a data type alias that uses the icon described by that data.
            Render each icon from packaged bytes data and add them to the dict under each alias. """
        data = pkgutil.get_data(package, path)
        lines = data.decode('utf-8').splitlines()
        [fmt], *items = csv.reader(map(str.strip, lines))
        for *aliases, xml_data in items:
            xml = fmt.format(xml_data).encode('utf-8')
            for n in aliases:
                self._icons[n] = xml

    def generate(self, obj:object) -> DebugData:
        """ Create a new debug data object from properties of <obj>. """
        data = DebugData(self.generate)
        type_params = TypeParams(type(obj))
        data.add_type_data(type_params)
        is_metacls = isinstance(obj, type) and issubclass(obj, type)
        icon = self._get_icon_data(type_params, is_metacls)
        val = self._value_repr(obj)
        data.add_value_data(val, icon)
        # Use the container type registry to make containers which match the object's properties.
        containers = CONTAINER_TYPES.match(obj)
        data.add_child_data(containers)
        return data

    def _get_icon_data(self, type_params:TypeParams, is_metacls:bool) -> bytes:
        """ Return the best of the given available icons out of a sequence of choices from most wanted to least. """
        choices = [*type_params.mro_names]
        # Metaclasses show a special icon.
        if is_metacls:
            choices.insert(0, "__METATYPE__")
        # Objects originating from the root package show a gear icon.
        if type_params.module.startswith(self._root_package):
            choices[-1] = "__COMPONENT__"
        return next(filter(None, map(self._icons.get, choices)), b"")
