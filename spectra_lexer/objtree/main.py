import os

from .container import CONTAINER_TYPES
from .data import ObjectData, ObjectDataFactory
from .format import MROGrapher, ValueRepr
from .icons import SVGIconFinder
from .qt import SVGIconRenderer, TreeColumn, TreeDialog, TreeItem, TreeItemModel
from .system import AutoImporter, package

# Relative path to default icon file.
ICON_PATH = "treeicons.txt"


def build_root(obj:object, root_package:str=None) -> ObjectData:
    # root_package - name of Python package for objects using the root component icon.
    matcher = CONTAINER_TYPES
    icon_finder = SVGIconFinder(root_package)
    icon_finder.load(os.path.join(os.path.dirname(__file__), ICON_PATH))
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


def build_model(root_data:ObjectData) -> TreeItemModel:
    icon_renderer = SVGIconRenderer()
    key_col = KeyColumn(icon_renderer)
    type_col = TypeColumn()
    value_col = ValueColumn()
    root_item = key_col.generate_item(root_data)
    return TreeItemModel(root_item, [key_col, type_col, value_col])


class NamespaceTreeDialog(TreeDialog):
    """ Tree dialog with icons and a standard column arrangement. """

    def set_namespace(self, namespace:dict, *, root_package:str=None, add_modules=True) -> None:
        if add_modules:
            namespace["modules"] = package.from_modules()
        root_data = build_root(namespace, root_package)
        item_model = build_model(root_data)
        self.set_model(item_model)
