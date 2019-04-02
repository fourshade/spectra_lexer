from itertools import islice
from typing import Callable

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QFont, QStandardItem, QStandardItemModel
from PyQt5.QtWidgets import QTreeView, QVBoxLayout

from .container import Container, MutableContainer
from .icon import IconFinder
from .repr import NodeRepr
from spectra_lexer.gui_qt.tools.dialog import ToolDialog

# Font color for data items in immutable containers.
COLOR_UNEDITABLE = QColor(96, 64, 64)
# Default maximum number of child nodes to generate.
CHILD_LIMIT = 200


class RowConstructor:
    """ Uses several classes to construct an entire tree row for display. """

    get_children: Callable   # Creates "containers" which handle the iterable contents or attributes of an object.
    get_icon: Callable       # Contains icons for each supported object type.
    get_value_str: Callable  # Custom repr function for displaying node values.

    def __init__(self, icon_dict:dict):
        self.get_children = Container.from_type
        self.get_icon = IconFinder(icon_dict).get_icon
        self.get_value_str = NodeRepr().repr

    def create_row(self, obj:object, key:object="ROOT", parent:Container=None):
        """ Create a new row containing info about an arbitrary Python object. It may have contents that expand. """
        # The first item (column 0) is the primary tree item with the key. Only it has an icon.
        children = self.get_children(obj)
        key_item = KeyItem(children, self.get_icon(obj), str(key))
        # The second item contains the type of object and/or item count (column 1).
        type_item = TypeItem(" - ".join([type(obj).__name__, *filter(None, map(str, children))]))
        # The third item contains the string value of the object (column 2).
        value_item = ValueItem(self.get_value_str(obj), key, parent)
        return [key_item, type_item, value_item]


class KeyItem(QStandardItem):
    """ Tree item for showing an object's name/key. May be expanded if the object has contents. """

    def __init__(self, children:list, *args):
        """ If there are children, add a dummy item to make the row expandable. """
        super().__init__(*args)
        self.children = children
        self.setEditable(False)
        if any(children):
            self.appendRow(QStandardItem("dummy"))

    def expand(self, constructor:RowConstructor) -> None:
        """ Remove any previous rows and expand this item, adding a row for each child. """
        self.removeRows(0, self.rowCount())
        for c in self.children:
            for key, obj in islice(c, CHILD_LIMIT):
                self.appendRow(constructor.create_row(obj, key, c))


class TypeItem(QStandardItem):
    """ Basic tree item for showing an object's type. """

    def __init__(self, *args):
        super().__init__(*args)
        self.setEditable(False)


class ValueItem(QStandardItem):
    """ Tree item for showing an object's value. The value may be edited if mutable. """

    def __init__(self, s:str, key:object, container:MutableContainer):
        super().__init__(s)
        self.original_data = s
        self.key = key
        self.container = container
        is_editable = isinstance(container, MutableContainer)
        self.setEditable(is_editable)
        if not is_editable:
            self.setForeground(COLOR_UNEDITABLE)

    def edit(self, constructor:RowConstructor) -> None:
        """ Attempt to change the value of a row's underlying object by editing its container. """
        try:
            # Since only strings can be entered, we must evaluate them as Python expressions.
            # Any exception is possible; just abort if one occurs.
            self.container.set(self.key, eval(self.data(Qt.DisplayRole)))
            # We have no idea what properties changed. Re-expand the parent item to be safe.
            self.parent().expand(constructor)
        except Exception:
            # If the new value was not a valid Python expression or editing failed another way, reset it.
            self.setData(self.original_data, Qt.DisplayRole)


class ObjectTreeDialog(ToolDialog):
    """ Qt tree dialog window object. """

    TITLE = "Python Object Tree View"
    SIZE = (600, 450)

    def make_layout(self, root_dict:dict, icon_dict:dict) -> None:
        """ Create the row constructor and item model and set the value edit callback. """
        constructor = RowConstructor(icon_dict)
        model = QStandardItemModel()
        model.setHorizontalHeaderLabels(["Name", "Type/Item Count", "Value"])
        model.itemChanged.connect(lambda item: item.edit(constructor))
        # Fill out the root level of the tree by changing the class on the existing root item.
        r_item = model.invisibleRootItem()
        r_item.__class__ = KeyItem
        r_item.children = constructor.get_children(root_dict)
        r_item.expand(constructor)
        # Create the tree widget and connect the expansion signal.
        w_tree = QTreeView(self)
        w_tree.setFont(QFont("Segoe UI", 9))
        w_tree.setModel(model)
        w_tree.expanded.connect(lambda idx: model.itemFromIndex(idx).expand(constructor))
        w_tree.header().setDefaultSectionSize(120)
        w_tree.header().resizeSection(0, 200)
        layout = QVBoxLayout(self)
        layout.addWidget(w_tree)
