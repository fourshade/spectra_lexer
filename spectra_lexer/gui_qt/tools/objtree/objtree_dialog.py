from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QIcon, QStandardItem, QStandardItemModel
from PyQt5.QtWidgets import QTreeView, QVBoxLayout

from .icon import IconFinder
from .node import Node
from spectra_lexer.gui_qt.tools.dialog import ToolDialog


class ObjectTreeItem(QStandardItem):
    """ Basic tree item. Holds a string value and can reset to its original value if edited. """

    def __init__(self, data:str, is_editable:bool, icon:QIcon=None):
        args = (data,) if icon is None else (icon, data)
        super().__init__(*args)
        self.setEditable(is_editable)
        self.reset = lambda: self.setData(data, Qt.DisplayRole)


class ObjectTreeModel(QStandardItemModel):
    """ Basic tree item model. Contains the callbacks for both expansion and editing. """

    icon_finder: IconFinder  # Returns an icon depending on an object's type.

    def __init__(self, root:Node, icon_dict:dict):
        """ Fill out the root level of the tree and set the value edit callback. """
        super().__init__()
        self.icon_finder = IconFinder(icon_dict)
        item = self.invisibleRootItem()
        item.expand = root.expand
        self.expand(item)
        self.setHorizontalHeaderLabels(["Name", "Type/Item Count", "Value"])
        self.itemChanged.connect(self.edit)

    def expand(self, item:ObjectTreeItem) -> None:
        """ Remove any previous rows and expand an item, adding a row for each child. """
        if item.expand is not None:
            item.removeRows(0, item.rowCount())
            for node in item.expand():
                self._add_row(item, node)

    def _add_row(self, parent:ObjectTreeItem, node:Node) -> None:
        """ The first item (column 0) is the primary node item. Only it has an icon.
            If there are children, add a dummy item to make the row expandable. """
        icon = self.icon_finder[node.icon_id]
        primary_item = ObjectTreeItem(node.key_str, False, icon)
        primary_item.expand = node.expand
        if node.expand is not None:
            primary_item.appendRow(QStandardItem("dummy"))
        # Contains the type of object and/or item count (column 1).
        type_item = ObjectTreeItem(node.type_str, False)
        # Contains the string value of the object (column 2).
        value_item = ObjectTreeItem(node.value_str, node.edit is not None)
        value_item.edit = node.edit
        parent.appendRow([primary_item, type_item, value_item])

    def edit(self, item:ObjectTreeItem) -> None:
        """ Change the value of a row's underlying object. """
        if item.edit is None or item.edit(item.data(Qt.DisplayRole)) is None:
            # If the new value was not a valid Python expression or editing failed another way, reset it.
            item.reset()
        else:
            # We have no idea what properties changed. Re-expand the parent to be safe.
            self.expand(item.parent() or self.invisibleRootItem())


class ObjectTreeDialog(ToolDialog):
    """ Qt tree dialog window object. """

    TITLE = "Python Object Tree View"
    SIZE = (600, 450)

    def make_layout(self, *args) -> None:
        """ Create the tree widget and item model and connect the expansion signal. """
        layout = QVBoxLayout(self)
        w_tree = QTreeView(self)
        w_tree.setFont(QFont("Segoe UI", 9))
        model = ObjectTreeModel(*args)
        w_tree.setModel(model)
        w_tree.expanded.connect(lambda idx: model.expand(model.itemFromIndex(idx)))
        w_tree.header().setDefaultSectionSize(120)
        w_tree.header().resizeSection(0, 200)
        layout.addWidget(w_tree)
