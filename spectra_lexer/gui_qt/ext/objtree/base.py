from collections import defaultdict
from itertools import islice
import pkgutil
from typing import Callable, Dict, Iterable, List

from PyQt5.QtCore import QAbstractItemModel, QModelIndex, QSize, Qt
from PyQt5.QtGui import QColor, QFont, QIcon, QImage, QPainter, QPixmap
from PyQt5.QtSvg import QSvgRenderer
from PyQt5.QtWidgets import QTreeView, QVBoxLayout

from .resources import IconPackage, RootDict
from .row import RowData
from ..dialog import ToolDialog


class IconRenderer:
    """ SVG renderer for static icons on transparent bitmap images. """

    _TRANSPARENT_WHITE = QColor.fromRgb(255, 255, 255, 0)

    _viewBox: QSize
    _render: Callable

    def __init__(self, xml:bytes):
        svg = QSvgRenderer(xml)
        self._viewbox = svg.viewBox().size()
        self._render = svg.render

    def generate(self, size:QSize=None, bg:QColor=_TRANSPARENT_WHITE) -> QIcon:
        """ Create a template with the given background color, render the element in place, and convert it to an icon.
            If no size is given, use the viewbox dimensions as pixel sizes. """
        im = QImage(size or self._viewbox, QImage.Format_ARGB32)
        im.fill(bg)
        with QPainter(im) as p:
            # Icons are small but important; set render hints for best quality.
            p.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
            self._render(p)
        return QIcon(QPixmap.fromImage(im))


class RowFormatter:
    """ Formats each tree item as a single row with a dict of parameters. """

    _FLAGS = Qt.ItemIsSelectable | Qt.ItemIsEnabled  # Default item flags. Items are black and selectable.

    _icons: Dict[str, QIcon]  # Dict of pre-rendered icons corresponding to data types.

    def __init__(self, icons:IconPackage):
        """ Render each icon from packaged bytes data and add them to a dict under each alias. """
        self._icons = {}
        for aliases, xml in icons.encode_all():
            icon = IconRenderer(xml).generate()
            for n in aliases:
                self._icons[n] = icon

    def _color(self, rgb:tuple, _cache={}) -> QColor:
        """ RGB color generator with a default argument cache. """
        if rgb in _cache:
            return _cache[rgb]
        color = _cache[rgb] = QColor(*rgb)
        return color

    def _get_icon(self, choices:Iterable[str]) -> QIcon:
        """ Return an available icon from a sequence of choices from most wanted to least. """
        return next(filter(None, map(self._icons.get, choices)), None)

    def __call__(self, data:RowData, parent:object=None) -> List[dict]:
        """ Assign the parent, item flags, and various pieces of data in string keys to Qt roles for item display.
            Column 0 is the primary tree item with the key and icon. Possible icons are based on type.
            Column 1 contains the type of object, item count, and/or a tooltip detailing the MRO.
            Column 2 contains the string value of the object. It may be edited if mutable. """
        get = data.get
        color = self._color(get("color") or (0, 0, 0))
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

    # Default maximum number of child object rows to show for each object.
    CHILD_LIMIT = 200
    # Captions and height for the header at the top of the window.
    HEADINGS = ["Name", "Type/Item Count", "Value"]
    HEADER_DATA = {Qt.Horizontal: {Qt.DisplayRole: HEADINGS,
                                   Qt.SizeHintRole: [QSize(0, 25)] * len(HEADINGS)}}

    _format_row: RowFormatter             # Formats each item data dict with flags and roles.
    _d: Dict[QModelIndex, List[list]]      # Contains all expanded parent model indices mapped to grids of items.
    _idx_to_item: Dict[QModelIndex, dict]  # Contains all generated model indices mapped to items.

    def __init__(self, root_dict:dict, formatter:RowFormatter):
        """ Create the index dictionaries and fill out the root level of the tree. """
        super().__init__()
        self._d = defaultdict(list)
        self._format_row = formatter
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

    def columnCount(self, *args) -> int:
        return len(self.HEADINGS)

    def headerData(self, section:int, orientation:int, role:int=None):
        d = self.HEADER_DATA.get(orientation, ())
        if role in d:
            return d[role][section]

    def setData(self, idx:QModelIndex, new_data:str, *args) -> bool:
        """ Attempt to change an object's value. Re-expand the parent on success, otherwise turn the item red. """
        # A blank field will not evaluate to anything; the user just clicked off of the field.
        if not new_data:
            return False
        # Either the value or the color will change, and either will affect the display, so return True.
        try:
            self.edit(idx)(new_data)
            self.expand(self.parent(idx))
        except Exception:
            # Non-standard container classes could raise anything, so just ignore the specifics.
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
            child_iter = islice(self.child_data(idx), self.CHILD_LIMIT)
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

    ICON_PATH = (__package__, "/treeicons.svg")  # Package and relative file path with all object tree icons.

    def make_layout(self, components:list, **kwargs) -> None:
        """ Create the tree widget and item model, connect the expansion signal, and format the header. """
        root_dict = RootDict(components, **kwargs)
        icon_data = pkgutil.get_data(*self.ICON_PATH)
        icons = IconPackage.decode(icon_data)
        formatter = RowFormatter(icons)
        model = ObjectTreeModel(root_dict, formatter)
        view = QTreeView(self)
        view.setFont(QFont("Segoe UI", 9))
        view.setUniformRowHeights(True)
        view.setModel(model)
        view.expanded.connect(model.expand)
        header = view.header()
        header.setDefaultSectionSize(120)
        header.resizeSection(0, 200)
        QVBoxLayout(self).addWidget(view)
