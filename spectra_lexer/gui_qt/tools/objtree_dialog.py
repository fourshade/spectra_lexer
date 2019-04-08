from collections import defaultdict
from functools import partialmethod
from itertools import islice
from typing import Dict, Iterable, List

from PyQt5.QtCore import QAbstractItemModel, QModelIndex, QSize, Qt
from PyQt5.QtGui import QColor, QFont, QIcon, QImage, QPainter, QPixmap
from PyQt5.QtSvg import QSvgRenderer
from PyQt5.QtWidgets import QTreeView, QVBoxLayout

from .dialog import ToolDialog
from spectra_lexer.utils import memoize

# Default maximum number of child objects to show for each object.
CHILD_LIMIT = 200
# Captions and height for the header at the top of the window.
HEADER_DATA = {Qt.DisplayRole: ["Name", "Type/Item Count", "Value"], Qt.SizeHintRole: [QSize(0, 25)] * 3}


class IconRenderer(dict):
    """ SVG icon dict that renders static icons on transparent bitmap images. """

    def __init__(self, xml_bytes:bytes, icon_ids:Dict[str, list]):
        """ Load an SVG XML string and create a blank template image with the viewbox size. """
        super().__init__()
        gfx = QSvgRenderer(xml_bytes)
        blank = QImage(gfx.viewBox().size(), QImage.Format_ARGB32)
        blank.fill(QColor.fromRgb(255, 255, 255, 0))
        # Create an icon dict using the SVG element IDs and their aliases.
        for k, names in icon_ids.items():
            # For each SVG element, copy the template, render the element in place, and convert it to an icon.
            im = QImage(blank)
            with QPainter(im) as p:
                # Icons are small but important; set render hints for every new painter to render in best quality.
                p.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
                gfx.render(p, k, gfx.boundsOnElement(k))
            icon = QIcon(QPixmap.fromImage(im))
            for n in names:
                self[n] = icon

    def __call__(self, choices:Iterable[str]) -> QIcon:
        """ Return an available icon from a sequence of choices from most wanted to least. """
        return next(filter(None, map(self.get, choices)), None)


class ItemFormatter:

    _flags: int             # Bit field of default item flags. Items are black and selectable.
    _role_map: List[tuple]  # Maps string keys to Qt roles, with a formatting function applied to the data.

    def __init__(self, **kwargs):
        """ Create the flags and role data map with the [caching] color generator and icon finder. """
        self._flags = Qt.ItemIsSelectable | Qt.ItemIsEnabled
        self._role_map = [("text",         Qt.DisplayRole,    lambda x: x),
                          ("tooltip",      Qt.ToolTipRole,    lambda x: x),
                          ("icon_choices", Qt.DecorationRole, IconRenderer(**kwargs)),
                          ("color",        Qt.ForegroundRole, memoize(lambda t: QColor(*t)))]

    def __call__(self, parent:QModelIndex, data:dict):
        """ Assign the parent, item flags, and various pieces of data in string keys to Qt roles for item display. """
        data.update({r: f(data[k]) for k, r, f in self._role_map if k in data}, parent=parent, flags=self._flags)
        if "edit" in data:
            data["flags"] |= Qt.ItemIsEditable


class ObjectTreeModel(QAbstractItemModel):
    """ A data model storing a tree of rows containing info about arbitrary Python objects. """

    _format_item = ItemFormatter           # Formats each item data dict with flags and roles.
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
        return 3

    def headerData(self, section:int, orientation:int, role:int=None):
        if orientation == Qt.Horizontal and role in HEADER_DATA:
            return HEADER_DATA[role][section]

    def setData(self, idx:QModelIndex, new_data:str, *args) -> bool:
        """ Attempt to change an object's value. Return True on success. """
        try:
            # Since only strings can be entered, we must evaluate them as Python expressions.
            # Any exception is possible; just abort if one occurs. Re-expand the parent if successful.
            self.data(idx, "edit")(eval(new_data))
            self.expand(self.parent(idx))
            return True
        except Exception:
            # If the current value was not a valid Python expression or editing failed another way, do nothing.
            return False

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
                    self._format_item(idx, item)
            # Add every new row at once.
            self.beginInsertRows(idx, 0, len(new_rows))
            rows += new_rows
            self.endInsertRows()


class ObjectTreeView(QTreeView):

    def __init__(self, parent:ToolDialog, **kwargs):
        """ Create the item model, format the header, and connect the expansion signal. """
        super().__init__(parent)
        self.setFont(QFont("Segoe UI", 9))
        self.setModel(ObjectTreeModel(**kwargs))
        self.header().setDefaultSectionSize(120)
        self.header().resizeSection(0, 200)
        self.expanded.connect(self.model().expand)


class ObjectTreeDialog(ToolDialog):
    """ Qt tree dialog window object. """

    TITLE = "Python Object Tree View"
    SIZE = (600, 450)

    def make_layout(self, resources:dict) -> None:
        """ Create the layout and tree widget. """
        QVBoxLayout(self).addWidget(ObjectTreeView(self, **resources))
