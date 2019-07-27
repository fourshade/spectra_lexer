from collections import defaultdict
from functools import lru_cache
from itertools import islice
from typing import Dict, Iterable, List

from PyQt5.QtCore import QAbstractItemModel, QModelIndex, QSize, Qt
from PyQt5.QtGui import QColor, QFont, QIcon
from PyQt5.QtWidgets import QDialog, QTreeView, QVBoxLayout

from .resources import IconData
from .row import RowData
from ..dialog import ToolDialog
from ...icon import IconRenderer

# Default maximum number of child objects to show for each object.
CHILD_LIMIT = 200
# Captions and height for the header at the top of the window.
HEADINGS = ["Name", "Type/Item Count", "Value"]
HEADER_DATA = {Qt.DisplayRole: HEADINGS, Qt.SizeHintRole: [QSize(0, 25)] * len(HEADINGS)}


@lru_cache(maxsize=None)
def _color(t:tuple=None) -> QColor:
    """ Caching color generator. """
    if t is None:
        return QColor(0, 0, 0)
    return QColor(*t)


class _RowFormatter:
    """ Formats each tree item as a single row with a dict of parameters. """

    _FLAGS = Qt.ItemIsSelectable | Qt.ItemIsEnabled  # Default item flags. Items are black and selectable.

    _icons: Dict[str, QIcon]  # Dict of pre-rendered icons corresponding to data types.

    def __init__(self, icon_data:IconData):
        """ Render each icon from bytes data and add them to a dict under each alias. """
        self._icons = {}
        for aliases, xml in icon_data:
            icon = IconRenderer(xml).generate()
            for n in aliases:
                self._icons[n] = icon

    def _get_icon(self, choices:Iterable[str]) -> QIcon:
        """ Return an available icon from a sequence of choices from most wanted to least. """
        return next(filter(None, map(self._icons.get, choices)), None)

    def __call__(self, data:RowData, parent:object=None) -> List[dict]:
        """ Assign the parent, item flags, and various pieces of data in string keys to Qt roles for item display.
            Column 0 is the primary tree item with the key and icon. Possible icons are based on type.
            Column 1 contains the type of object, item count, and/or a tooltip detailing the MRO.
            Column 2 contains the string value of the object. It may be edited if mutable. """
        get = data.get
        color = _color(get("color"))
        row = []
        for s in ("key", "type", "value"):
            item = {"parent": parent,
                    "flags": Qt.ItemFlags(self._FLAGS),
                    Qt.ForegroundRole: color,
                    Qt.DisplayRole: get(f'{s}_text', "")}
            tooltip = get(f'{s}_tooltip')
            if tooltip is not None:
                item[Qt.ToolTipRole] = f'<pre>{tooltip}</pre>'
            edit = get(f'{s}_edit')
            if edit is not None:
                item["edit"] = edit
                item["flags"] |= Qt.ItemIsEditable
            row.append(item)
        key_item, type_item, _ = row
        children = get("child_data")
        if children is not None:
            key_item["hasChildren"] = True
            key_item["child_data"] = children
        icon = get("icon_choices")
        if icon is not None:
            key_item[Qt.DecorationRole] = self._get_icon(icon)
        count = get("item_count")
        if count is not None:
            type_item[Qt.DisplayRole] += f' - {count} item{"s" * (count != 1)}'
        return row


class ObjectTreeModel(QAbstractItemModel):
    """ A data model storing a tree of rows containing info about arbitrary Python objects. """

    _format_row: _RowFormatter             # Formats each item data dict with flags and roles.
    _d: Dict[QModelIndex, List[list]]      # Contains all expanded parent model indices mapped to grids of items.
    _idx_to_item: Dict[QModelIndex, dict]  # Contains all generated model indices mapped to items.

    def __init__(self, root_dict:dict, icon_data:IconData):
        """ Create the row formatter and index dictionaries and fill out the root level of the tree. """
        super().__init__()
        self._d = defaultdict(list)
        self._format_row = _RowFormatter(icon_data)
        root_idx = QModelIndex()
        root_data = RowData(root_dict)
        root_item = self._format_row(root_data)[0]
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

    def parent(self, idx:QModelIndex=None) -> QModelIndex:
        return self.data(idx, "parent")

    def flags(self, idx:QModelIndex) -> Qt.ItemFlags:
        return self.data(idx, "flags")

    def hasChildren(self, idx:QModelIndex=None, *args) -> bool:
        return self.data(idx, "hasChildren", False)

    def edit(self, idx:QModelIndex):
        return self.data(idx, "edit")

    def child_data(self, idx:QModelIndex) -> Iterable[RowData]:
        return self.data(idx, "child_data", ())

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
        if self.edit(idx)(new_data):
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
            child_iter = islice(self.child_data(idx), CHILD_LIMIT)
            # Format each new row with items containing flags and Qt roles for display.
            new_rows = [self._format_row(data, idx) for data in child_iter]
            # Add every new row at once.
            self.beginInsertRows(idx, 0, len(new_rows))
            rows += new_rows
            self.endInsertRows()


class ObjectTreeDialog(ToolDialog):
    """ Qt tree dialog window object. """

    TITLE: str = "Python Object Tree View"
    SIZE: tuple = (600, 450)

    def make_layout(self, *args) -> None:
        """ Create the tree widget and item model, connect the expansion signal, and format the header. """
        view = QTreeView(self)
        view.setFont(QFont("Segoe UI", 9))
        view.setUniformRowHeights(True)
        model = ObjectTreeModel(*args)
        view.setModel(model)
        view.expanded.connect(model.expand)
        header = view.header()
        header.setDefaultSectionSize(120)
        header.resizeSection(0, 200)
        QVBoxLayout(self).addWidget(view)
