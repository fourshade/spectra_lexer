from types import MappingProxyType
from typing import Callable

from PyQt5.QtCore import QModelIndex, Qt
from PyQt5.QtGui import QFont, QStandardItem, QStandardItemModel
from PyQt5.QtWidgets import QTreeView, QVBoxLayout, QWidget

from .node import NodeData
from spectra_lexer.gui_qt.tools.dialog import ToolDialog


class NodeItem(QStandardItem):
    """ GUI object for a row in a object tree. Does not actually contain children until expansion is attempted. """

    type_item: QStandardItem   # Contains the type of object and/or item count, column 1.
    value_item: QStandardItem  # Contains the string value of the object, column 2.
    original_value: str        # Original value string at initialization, in case an edit fails.
    get_children: Callable     # Callback for when the user expands this item.
    edit: Callable             # Callback for when the user edits the object's value.

    def __init__(self, node:NodeData):
        """ Create a primary node item with the name and add standard items for other fields. """
        name, dtype, dvalue = node.info()
        super().__init__(name)
        self.setEditable(False)
        self.type_item = QStandardItem(dtype)
        self.type_item.setEditable(False)
        self.value_item = QStandardItem(dvalue)
        self.value_item.setEditable(node.is_editable())
        self.original_value = dvalue
        self.get_children = node.children
        self.edit = node.set_value
        if node:
            # If there are children, add a dummy item to make the row expandable.
            self.appendRow(QStandardItem("dummy"))

    def expand(self):
        """ When the user expands the row, remove the previous items and add a row for each child. """
        self.removeRows(0, self.rowCount())
        for node in self.get_children():
            # The first item in each column is the main node with children; the rest are just strings.
            item = NodeItem(node)
            self.appendRow([item, item.type_item, item.value_item])


class ObjectTreeModel(QStandardItemModel):
    """ Basic tree item model. Contains the callbacks for both expansion and editing. """

    def __init__(self, root:NodeItem):
        """ Fill out the root level of the tree and set the edit callback. """
        super().__init__()
        # We can't swap out the model's root item, so we expand the given one and steal all of its rows.
        root.expand()
        for i in range(root.rowCount()):
            self.invisibleRootItem().appendRow(root.takeRow(0))
        self.setHorizontalHeaderLabels(["Name", "Type/Item Count", "Value"])
        self.itemChanged.connect(self.edit_value)

    def edit_value(self, item:QStandardItem):
        """ Change the value of a row's underlying object by sending a request to the node data. """
        row = item.row()
        parent = item.parent()
        primary = parent.child(row, 0)
        edited_value = item.data(Qt.DisplayRole)
        if edited_value == primary.original_value:
            return
        new_node = primary.edit(edited_value)
        if new_node is None:
            # If the new value was not a valid Python expression, reset it.
            item.setData(primary.original_value, Qt.DisplayRole)
        else:
            # We have no idea what properties changed. Re-expand the parent to be safe.
            parent.expand()

    def on_expand(self, idx:QModelIndex) -> None:
        self.itemFromIndex(idx).expand()


class ObjectTreeWidget(QTreeView):
    """ Formatted text widget meant to display plaintext interpreter input and output. """

    def __init__(self, parent:ToolDialog, root_data:NodeData):
        """ Create the item model and connect the expansion signal (only the widget can detect this). """
        super().__init__(parent)
        self.setFont(QFont("Segoe UI", 9))
        model = ObjectTreeModel(NodeItem(root_data))
        self.setModel(model)
        self.header().setDefaultSectionSize(120)
        self.header().resizeSection(0, 200)
        self.expanded.connect(model.on_expand)


class ObjectTreeDialog(ToolDialog):
    """ Qt tree dialog window object. """

    TITLE = "Python Object Tree View"
    SIZE = (600, 450)

    w_tree: ObjectTreeWidget = None  # The only window content; a giant tree view.
    root: NodeData                   # Dict of variables at the top level of the tree.

    def __init__(self, parent:QWidget, submit_cb:Callable, root_vars:dict):
        """ Create the initial tree structure from a dict. Make it read-only to prevent top-level editing. """
        self.root = NodeData("ROOT", MappingProxyType(root_vars))
        super().__init__(parent, submit_cb)

    def make_layout(self) -> None:
        """ Create and add the sole widget to a vertical layout. """
        layout = QVBoxLayout(self)
        self.w_tree = ObjectTreeWidget(self, self.root)
        layout.addWidget(self.w_tree)
