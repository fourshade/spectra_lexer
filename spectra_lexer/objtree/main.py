import pkgutil

from .container import CONTAINER_TYPES
from .data import ObjectData, ObjectDataFactory
from .format import MROGrapher, ValueRepr
from .icons import SVGIconFinder
from .qt import SVGIconRenderer, TreeColumn, TreeDialog, TreeItem, TreeItemModel
from .system import AutoImporter, package


class RootDataFactory:

    def __init__(self, *, root_package:str=None, icon_package=__package__, icon_path="/treeicons.csv") -> None:
        self._root_package = root_package  # Name of Python package for objects using the root component icon.
        self._icon_package = icon_package  # Name of Python package containing the file with all object tree icons.
        self._icon_path = icon_path        # Relative path to icon file.

    def root_from_namespace(self, namespace:dict, *, add_modules=True) -> ObjectData:
        if add_modules:
            namespace["modules"] = package.modules()
        return self.root_from_object(namespace)

    def load_icons(self) -> SVGIconFinder:
        icon_finder = SVGIconFinder(self._root_package)
        icon_csv = pkgutil.get_data(self._icon_package, self._icon_path)
        icon_finder.load_csv(icon_csv)
        return icon_finder

    def root_from_object(self, obj:object) -> ObjectData:
        icon_finder = self.load_icons()
        matcher = CONTAINER_TYPES
        value_repr = ValueRepr().repr
        mro_grapher = MROGrapher().draw_graph
        eval_ns = AutoImporter.eval_namespace()
        factory = ObjectDataFactory(matcher, icon_finder, value_repr, mro_grapher, eval_ns)
        return factory.generate(obj)


class KeyColumn(TreeColumn):
    """ Column 0 is the primary tree item with the key, icon, and children. Possible icons are based on type. """
    heading = "Name"
    width = 200

    def __init__(self, icon_renderer:SVGIconRenderer) -> None:
        self._icon_renderer = icon_renderer

    def _format_item(self, item:TreeItem, data:ObjectData) -> None:
        item.set_color(*data.color)
        item.set_text(data.key_text)
        item.set_tooltip(data.key_tooltip)
        item.set_edit_cb(data.op_move)
        item.set_delete_cb(data.op_delete)
        item.set_children(data.children)
        icon_xml = data.icon_data
        if icon_xml:
            icon = self._icon_renderer.render(icon_xml)
            item.set_icon(icon)


class TypeColumn(TreeColumn):
    """ Column 1 contains the type of object, item count, and/or a tooltip detailing the MRO. """
    heading = "Type/Item Count"
    width = 120

    def _format_item(self, item:TreeItem, data:ObjectData) -> None:
        item.set_color(*data.color)
        text = data.type_text
        count = data.item_count
        if count is not None:
            text += f' - {count} item{"s" * (count != 1)}'
        item.set_text(text)
        item.set_tooltip(data.type_graph)
        item.set_delete_cb(data.op_delete)


class ValueColumn(TreeColumn):
    """ Column 2 contains the string value of the object. It may be edited if mutable. """
    heading = "Value"
    width = 230

    def _format_item(self, item:TreeItem, data:ObjectData) -> None:
        item.set_color(*data.color)
        item.set_text(data.value_text)
        item.set_tooltip(data.value_tooltip)
        item.set_edit_cb(data.op_edit)
        item.set_delete_cb(data.op_delete)


class NamespaceTreeDialog(TreeDialog):
    """ Tree dialog with icons and a standard column arrangement. """

    def set_namespace(self, namespace:dict, *, add_modules=True, **kwargs) -> None:
        factory = RootDataFactory(**kwargs)
        root_data = factory.root_from_namespace(namespace, add_modules=add_modules)
        icon_renderer = SVGIconRenderer()
        key_col = KeyColumn(icon_renderer)
        type_col = TypeColumn()
        value_col = ValueColumn()
        root_item = key_col.generate_item(root_data)
        item_model = TreeItemModel(root_item, [key_col, type_col, value_col])
        self.set_model(item_model)
