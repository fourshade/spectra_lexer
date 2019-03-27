from operator import methodcaller
from typing import Callable

from PyQt5.QtCore import QModelIndex, Qt
from PyQt5.QtGui import QFont, QStandardItem, QStandardItemModel
from PyQt5.QtWidgets import QTreeView, QVBoxLayout, QWidget

from .node import NodeData
from spectra_lexer.gui_qt.tools.dialog import ToolDialog


class ValueItem(QStandardItem):
    """ Editable value field. Sends info to its parent to accomplish the editing task. """

    def __init__(self, key:str, v_str:str, edit_callback:Callable):
        super().__init__(v_str)
        self._key = key
        self._edit_callback = edit_callback

    def edit_value(self):
        """ Change the value of the underlying object by sending a request to the node data. """
        edited_value = self.data(Qt.DisplayRole)
        new_v_str = self._edit_callback(self._key, edited_value)
        self.setData(new_v_str, Qt.DisplayRole)


class NodeItem(QStandardItem):
    """ GUI object for a row in a object tree. Does not actually contain children until expansion is attempted. """

    sub_items: list  # Extra items for fields in other columns.

    def __init__(self, node:NodeData):
        """ Create a primary node item with the name and add standard items for other fields. """
        name, dtype, dvalue, self.children = node.fields()
        super().__init__(name)
        self.setEditable(False)
        items = self.sub_items = [QStandardItem(dtype), ValueItem(name, dvalue, node.set_value)]
        items[0].setEditable(False)
        if self.children:
            # Add a dummy item to make the row expandable and make the value uneditable.
            self.appendRow(QStandardItem("dummy"))
            items[1].setEditable(False)

    def expand(self):
        """ When the user expands the row, remove the previous items and add a row for each child. """
        self.removeRows(0, self.rowCount())
        for node in self.children:
            # The first item in each column is the main node with children; the rest are just strings.
            item = NodeItem(node)
            self.appendRow([item, *item.sub_items])


class ObjectTreeWidget(QTreeView):
    """ Formatted text widget meant to display plaintext interpreter input and output. """

    def __init__(self, parent:ToolDialog, root_data:NodeData):
        super().__init__(parent)
        self.setFont(QFont("Segoe UI", 9))
        model = QStandardItemModel()
        model.setHorizontalHeaderLabels(["Name", "Type", "Value/Item Count"])
        root_item = NodeItem(root_data)
        root_item.expand()
        for i in range(root_item.rowCount()):
            model.invisibleRootItem().appendRow(root_item.takeRow(0))
        model.itemChanged.connect(methodcaller("edit_value"))
        self.setModel(model)
        self.header().setDefaultSectionSize(120)
        self.header().resizeSection(0, 200)
        self.expanded.connect(self.on_expand)

    def on_expand(self, idx:QModelIndex) -> None:
        self.model().itemFromIndex(idx).expand()


class ObjectTreeDialog(ToolDialog):
    """ Qt tree dialog window object. """

    TITLE = "Python Object Tree View"
    SIZE = (600, 450)

    w_tree: ObjectTreeWidget = None  # The only window content; a giant tree view
    root: NodeData = {}              # Dict of variables at the top level of the tree.

    def __init__(self, parent:QWidget, submit_cb:Callable, root_vars:dict):
        """ Create the initial tree structure. """
        self.root = NodeData("ROOT", root_vars)
        super().__init__(parent, submit_cb)

    def make_layout(self) -> None:
        """ Create and add the sole widget to a vertical layout. """
        layout = QVBoxLayout(self)
        self.w_tree = ObjectTreeWidget(self, self.root)
        layout.addWidget(self.w_tree)
