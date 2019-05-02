from collections import defaultdict
from functools import partialmethod
from itertools import islice
from typing import Dict, List

from PyQt5.QtCore import QAbstractItemModel, QModelIndex, QSize, Qt
from PyQt5.QtGui import QColor, QFont
from PyQt5.QtWidgets import QDialog, QTreeView, QVBoxLayout, QWidget

from .format import ItemFormatter
from spectra_lexer.gui import ObjectTreeTool

# Default maximum number of child objects to show for each object.
CHILD_LIMIT = 200
# Captions and height for the header at the top of the window.
HEADINGS = ["Name", "Type/Item Count", "Value"]
HEADER_DATA = {Qt.DisplayRole: HEADINGS, Qt.SizeHintRole: [QSize(0, 25)] * len(HEADINGS)}


class ObjectTreeModel(QAbstractItemModel):
    """ A data model storing a tree of rows containing info about arbitrary Python objects. """

    _format_item: ItemFormatter            # Formats each item data dict with flags and roles.
    _d: Dict[QModelIndex, List[list]]      # Contains all expanded parent model indices mapped to grids of items.
    _idx_to_item: Dict[QModelIndex, dict]  # Contains all generated model indices mapped to items.

    def __init__(self, root_item:dict, **kwargs):
        """ Create the formatter and index dictionaries and fill out the root level of the tree. """
        super().__init__()
        self._format_item = ItemFormatter(**kwargs)
        self._d = defaultdict(list)
        root_idx = QModelIndex()
        self._idx_to_item = defaultdict(dict, {root_idx: root_item})
        self.expand(root_idx)

    def index(self, row:int, col:int, parent:QModelIndex=None, *args) -> QModelIndex:
        try:
            r_item = self._d[parent][row][col]
            idx = self.createIndex(row, col, r_item)
            self._idx_to_item[idx] = r_item
            return idx
        except IndexError:
            return QModelIndex()

    def data(self, idx:QModelIndex, role=None, default=None):
        return self._idx_to_item[idx].get(role, default)

    parent = partialmethod(data, role="parent")
    flags = partialmethod(data, role="flags")
    hasChildren = partialmethod(data, role="has_children", default=False)

    def rowCount(self, idx:QModelIndex=None, *args) -> int:
        return len(self._d[idx])

    def columnCount(self, idx:QModelIndex=None, *args) -> int:
        return len(HEADINGS)

    def headerData(self, section:int, orientation:int, role:int=None):
        if orientation == Qt.Horizontal and role in HEADER_DATA:
            return HEADER_DATA[role][section]

    def setData(self, idx:QModelIndex, new_data:str, *args) -> bool:
        """ Attempt to change an object's value. Re-expand the parent on success, otherwise turn the item red. """
        # A blank field will not evaluate to anything; the user just clicked off of the field.
        if not new_data:
            return False
        # Either the value or the color will change, and either will affect the display, so return True.
        if self.data(idx, "edit")(new_data):
            self.expand(self.parent(idx))
        else:
            # The item will return to the normal color after re-expansion.
            self._idx_to_item[idx][Qt.ForegroundRole] = QColor(192, 0, 0)
        return True

    def expand(self, idx:QModelIndex) -> None:
        """ Add (or replace) all children on the item found at this index from internal object data. """
        rows = self._d[idx]
        if rows:
            # If there are existing child rows, get rid of them first.
            self.beginRemoveRows(idx, 0, len(rows))
            rows.clear()
            self.endRemoveRows()
        if self.hasChildren(idx):
            # Rows of raw data items are generated only when iterating over the "child_data" entry.
            # It is a lazy iterator, so we can limit the rows generated using islice.
            new_rows = list(islice(self.data(idx, "child_data"), CHILD_LIMIT))
            # Format every item in each new row with flags and Qt roles for display.
            for row in new_rows:
                for item in row:
                    item["parent"] = idx
                    self._format_item(item)
            # Add every new row at once.
            self.beginInsertRows(idx, 0, len(new_rows))
            rows += new_rows
            self.endInsertRows()


class ObjectTreeView(QTreeView):

    def __init__(self, parent:QDialog, model:ObjectTreeModel):
        """ Create the item model, format the header, and connect the expansion signal. """
        super().__init__(parent)
        self.setFont(QFont("Segoe UI", 9))
        self.setModel(model)
        self.header().setDefaultSectionSize(120)
        self.header().resizeSection(0, 200)
        self.setUniformRowHeights(True)
        self.expanded.connect(model.expand)


class ObjectTreeDialog(QDialog):
    """ Qt tree dialog window object. """

    TITLE: str = "Python Object Tree View"  # Dialog window title string.
    SIZE: tuple = (600, 450)                # Dimensions in pixels: (width, height).

    def __init__(self, parent:QWidget, resources:dict):
        """ Create the root UI dialog window, layout, item model, and tree widget. """
        super().__init__(parent, Qt.CustomizeWindowHint | Qt.Dialog | Qt.WindowTitleHint | Qt.WindowCloseButtonHint)
        self.setWindowTitle(self.TITLE)
        self.resize(*self.SIZE)
        self.setMinimumSize(*self.SIZE)
        self.setSizeGripEnabled(False)
        model = ObjectTreeModel(**resources)
        QVBoxLayout(self).addWidget(ObjectTreeView(self, model))


class GUIQtObjectTreeTool(ObjectTreeTool):
    """ Component for interactive tree operations. """

    window = resource("gui:window", desc="Main window object. Must be the parent of any new dialogs.")

    def open_dialog(self, *args) -> None:
        ObjectTreeDialog(self.window, *args).show()
