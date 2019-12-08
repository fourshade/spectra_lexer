from collections import defaultdict
from itertools import islice
from typing import Any, Callable, Iterable, Iterator, Sequence, TypeVar

from PyQt5.QtCore import QAbstractItemModel, QModelIndex, QSize, Qt
from PyQt5.QtGui import QColor, QFont, QIcon
from PyQt5.QtWidgets import QDialog, QTreeView, QVBoxLayout

# Marker for debug data objects.
DATA_OBJ = TypeVar("DATA_OBJ")


class ObjectTreeItem:
    """ A single item in the tree. Contains model data in attributes and role data in the dict. """

    def __init__(self, parent:QModelIndex=None) -> None:
        self._parent = parent  # Model index of the direct parent of this item (None for the root).
        self._roles = {}       # Contains all display data for this item indexed by Qt roles (really ints).
        self._edit_cb = None   # Callback to edit the value of this item, or None if not editable.
        self._child_iter = ()  # Iterable to produce child rows. Must evaluate as boolean False if there are none.

    def role_data(self, role:int) -> Any:
        """ Return a role data item. Used heavily by the Qt item model. """
        return self._roles.get(role)

    def parent(self) -> QModelIndex:
        """ Return this item's parent index. Used heavily by the Qt item model. """
        return self._parent

    def flags(self) -> Qt.ItemFlags:
        """ Return a set of Qt display flags. Items are black and selectable by default. """
        flags = Qt.ItemIsSelectable | Qt.ItemIsEnabled
        if self._edit_cb is not None:
            flags |= Qt.ItemIsEditable
        return flags

    def has_children(self) -> bool:
        """ Return True if at least one child data object will be yielded on iteration. """
        return bool(self._child_iter)

    def __iter__(self) -> Iterator[DATA_OBJ]:
        """ Yield all available child data objects. """
        return iter(self._child_iter)

    def edit(self, new_value:str) -> bool:
        """ Attempt to change the object's actual value. Return True on success. """
        try:
            self._edit_cb(new_value)
            return True
        except Exception:
            # Non-standard container classes could raise anything, so just ignore the specifics.
            # Turn the item red. The item will return to the normal color after re-expansion.
            self.set_color(192, 0, 0)
            return False

    def set_text(self, text:str) -> None:
        """ Set the primary text as shown in the tree columns. """
        self._roles[Qt.DisplayRole] = text

    def set_color(self, r:int, g:int, b:int) -> None:
        """ Set the color of the item's primary text. """
        self._roles[Qt.ForegroundRole] = QColor(r, g, b)

    def set_tooltip(self, tooltip:str) -> None:
        """ Set text to appear over the item as a tooltip on mouseover. """
        self._roles[Qt.ToolTipRole] = f'<pre>{tooltip}</pre>'

    def set_icon(self, icon:QIcon) -> None:
        """ Set an icon to appear to the left of the item's text. """
        self._roles[Qt.DecorationRole] = icon

    def set_edit_cb(self, edit:Callable[[str], None]) -> None:
        """ Set a callback that uses a string to edit the underlying object's value. """
        self._edit_cb = edit

    def set_children(self, child_iter:Iterable[DATA_OBJ]) -> None:
        """ Set an iterable that will produce child data objects. It must be reusable. """
        self._child_iter = child_iter


class ObjectTreeColumn:
    """ Abstract class for a tree column with a certain item format. """

    def __init__(self, heading:str) -> None:
        self.heading = heading  # Heading that appears above this column.

    def format_item(self, item:ObjectTreeItem, data:DATA_OBJ) -> None:
        """ Format a tree item with attributes and Qt display roles from a data structure. """
        raise NotImplementedError


class ObjectTreeItemModel(QAbstractItemModel):
    """ A data model storing a tree of rows containing info about arbitrary Python objects. """

    _ROOT_IDX = QModelIndex()  # Sentinel value for the index of the root item.

    def __init__(self, root_item:ObjectTreeItem, columns:Sequence[ObjectTreeColumn], *,
                 child_limit=200, header_height=25) -> None:
        super().__init__()
        self._idx_to_item = {self._ROOT_IDX: root_item}  # Contains model indices mapped to tree items.
        self._idx_to_children = defaultdict(list)        # Contains model indices mapped to grids of their children.
        self._columns = columns                          # Item formatter for each column in the tree.
        self._child_limit = child_limit                  # Maximum number of child rows to show for each object.
        self._header_height = header_height              # Height of column headers in pixels.

    def index(self, row:int, col:int, parent:QModelIndex=_ROOT_IDX, *args) -> QModelIndex:
        try:
            item = self._idx_to_children[parent][row][col]
            idx = self.createIndex(row, col, item)
            self._idx_to_item[idx] = item
            return idx
        except IndexError:
            return self._ROOT_IDX

    def data(self, idx:QModelIndex, role:int=Qt.DisplayRole) -> Any:
        return self._idx_to_item[idx].role_data(role)

    def parent(self, idx:QModelIndex=_ROOT_IDX) -> QModelIndex:
        return self._idx_to_item[idx].parent()

    def flags(self, idx:QModelIndex) -> Qt.ItemFlags:
        return self._idx_to_item[idx].flags()

    def hasChildren(self, idx:QModelIndex=_ROOT_IDX, *args) -> bool:
        return self._idx_to_item[idx].has_children()

    def rowCount(self, idx:QModelIndex=_ROOT_IDX, *args) -> int:
        return len(self._idx_to_children[idx])

    def columnCount(self, *args) -> int:
        return len(self._columns)

    def headerData(self, section:int, orientation:int, role:int=None) -> Any:
        """ Return captions or height for the header at the top of the window (or None for other roles). """
        if orientation == Qt.Horizontal:
            if role == Qt.DisplayRole:
                return self._columns[section].heading
            if role == Qt.SizeHintRole:
                return QSize(0, self._header_height)

    def setData(self, idx:QModelIndex, new_value:str, *args) -> bool:
        """ Attempt to change an object's value. Re-expand the parent on success. """
        # A blank field will not evaluate to anything; the user just clicked off of the field.
        if not new_value:
            return False
        item = self._idx_to_item[idx]
        if item.edit(new_value):
            self.expand(item.parent())
        # Either the value or the color will change, and either will affect the display, so return True.
        return True

    def expand(self, idx:QModelIndex=_ROOT_IDX) -> None:
        """ Add (or replace) all children on the item found at this index from its object data. """
        child_rows = self._idx_to_children[idx]
        if child_rows:
            # If there are existing child rows, get rid of them first.
            self.beginRemoveRows(idx, 0, len(child_rows))
            child_rows.clear()
            self.endRemoveRows()
        # Generate child data objects by iterating over the parent item up to a limit using islice.
        item = self._idx_to_item[idx]
        child_data = list(islice(item, self._child_limit))
        # Create, format, and add new rows of child items to the tree from the data.
        self.beginInsertRows(idx, 0, len(child_data))
        for data in child_data:
            item_row = []
            for col in self._columns:
                item = ObjectTreeItem(idx)
                col.format_item(item, data)
                item_row.append(item)
            child_rows.append(item_row)
        self.endInsertRows()


class ObjectTreeTool:
    """ Qt tree dialog window tool. """

    def __init__(self, dialog:QDialog) -> None:
        self._dialog = dialog             # Base dialog object.
        self._w_view = QTreeView(dialog)  # Central tree view widget.

    def set_model(self, item_model:ObjectTreeItemModel) -> None:
        """ Connect an item model to the tree view widget and format the header. """
        item_model.expand()
        self._w_view.setModel(item_model)
        self._w_view.expanded.connect(item_model.expand)
        header = self._w_view.header()
        header.setDefaultSectionSize(120)
        header.resizeSection(0, 200)

    def display(self) -> None:
        """ Fill out the dialog with widgets and show it. """
        self._w_view.setFont(QFont("Segoe UI", 9))
        self._w_view.setUniformRowHeights(True)
        layout = QVBoxLayout(self._dialog)
        layout.addWidget(self._w_view)
        self._dialog.show()
