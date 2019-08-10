from collections import defaultdict
from itertools import islice
from typing import Any, Callable, Dict, Iterable, List

from PyQt5.QtCore import QAbstractItemModel, QModelIndex, QSize, Qt
from PyQt5.QtGui import QColor, QFont, QIcon, QImage, QPainter, QPixmap
from PyQt5.QtSvg import QSvgRenderer
from PyQt5.QtWidgets import QTreeView, QVBoxLayout

from .dialog import ToolDialog
from spectra_lexer.system import DebugData, DebugTree


class TreeItem:
    """ A single item in a row of the tree. Contains model data in attributes and role data in the dict. """

    HEADING: str = "UNDEFINED"  # Heading that appears above this item type's column.

    parent: QModelIndex    # Model index of the direct parent of this item (None for the root).
    flags: Qt.ItemFlags = Qt.ItemIsSelectable | Qt.ItemIsEnabled  # Default item flags. Items are black and selectable.
    edit: Callable = None  # Callback to edit the value of this item, or None if not editable.
    child_data: Iterable[DebugData] = None  # Iterable to produce child rows, or None if there are no children.

    _roles: Dict[int, Any]  # Contains all Qt role display data for this item.

    def __init__(self, parent:QModelIndex, data:DebugData, *args):
        """ Assign the parent, item flags, and various pieces of data in string keys to Qt roles for item display. """
        self._roles = {}
        self.parent = parent
        self.set_color(data.color)

    def role_data(self, role:int) -> Any:
        return self._roles.get(role)

    def set_text(self, text:str) -> None:
        self._roles[Qt.DisplayRole] = text

    def set_color(self, rgb:tuple, _cache={}) -> None:
        """ RGB color generator with a default argument cache. """
        if rgb in _cache:
            color = _cache[rgb]
        else:
            color = _cache[rgb] = QColor(*rgb)
        self._roles[Qt.ForegroundRole] = color

    def set_tooltip(self, tooltip:str) -> None:
        self._roles[Qt.ToolTipRole] = f'<pre>{tooltip}</pre>'

    def set_edit_cb(self, edit:Callable) -> None:
        if edit is not None:
            self.edit = edit
            self.flags = Qt.ItemFlags(self.flags) | Qt.ItemIsEditable


class KeyItem(TreeItem):
    """ Column 0 is the primary tree item with the key and icon. Possible icons are based on type. """

    HEADING = "Name"

    def __init__(self, parent:QModelIndex, data:DebugData, icons:Dict[str, QIcon]=()) -> None:
        super().__init__(parent, data)
        self.set_text(data.key_text)
        self.set_tooltip(data.key_tooltip)
        self.set_edit_cb(data.key_edit)
        self.child_data = data.child_data
        self.set_icon(data.choose_icon(icons))

    def set_icon(self, icon:QIcon) -> None:
        self._roles[Qt.DecorationRole] = icon


class TypeItem(TreeItem):
    """ Column 1 contains the type of object, item count, and/or a tooltip detailing the MRO. """

    HEADING = "Type/Item Count"

    def __init__(self, parent:QModelIndex, data:DebugData, *args) -> None:
        super().__init__(parent, data)
        text = data.type_text
        item_count = data.item_count
        if item_count is not None:
            text += f' - {item_count} item{"s" * (item_count != 1)}'
        self.set_text(text)
        self.set_tooltip(data.type_graph)


class ValueItem(TreeItem):
    """ Column 2 contains the string value of the object. It may be edited if mutable. """

    HEADING = "Value"

    def __init__(self, parent:QModelIndex, data:DebugData, *args) -> None:
        super().__init__(parent, data)
        self.set_text(data.value_text)
        self.set_tooltip(data.value_tooltip)
        self.set_edit_cb(data.value_edit)


class RowModel:
    """ Formats each tree item as a single row with a dict of parameters. """

    # Determines what columns appear in the tree.
    COL_TYPES = (KeyItem, TypeItem, ValueItem)

    _icons: Dict[str, QIcon]  # Dict of pre-rendered icons corresponding to data types.
    _child_limit: int         # Maximum number of child object rows to show for each object.

    def __init__(self, icons:Dict[str, QIcon], child_limit:int=200):
        self._icons = icons
        self._child_limit = child_limit

    def expand(self, item_idx:QModelIndex, item:TreeItem) -> List[List[TreeItem]]:
        """ Generate rows of tree items by iterating over the "child_data" entry up to a limit.
            It is a lazy iterator, so we can limit the rows generated using islice. """
        child_data = item.child_data
        if child_data is not None:
            child_iter = islice(child_data, self._child_limit)
            return [[cls(item_idx, data, self._icons) for cls in self.COL_TYPES] for data in child_iter]
        return []

    def col_count(self) -> int:
        return len(self.COL_TYPES)

    def col_data(self, role:int, section:int) -> Any:
        """ Return captions or height for the header at the top of the window (or None for other roles). """
        if role == Qt.DisplayRole:
            return self.COL_TYPES[section].HEADING
        if role == Qt.SizeHintRole:
            return QSize(0, 25)


class RenderedIconDict(dict):
    """ SVG icon dict that renders SVG bytes data on transparent bitmap images. """

    _TRANSPARENT_WHITE = QColor.fromRgb(255, 255, 255, 0)

    _bg: QColor

    def __init__(self, xml_dict:Dict[str, bytes], bg:QColor=_TRANSPARENT_WHITE):
        """ Render each icon from packaged bytes data and add them to a dict under each alias.
            Some aliases may use the same icon; to avoid rendering these multiple times, use a memo. """
        super().__init__()
        self._bg = bg
        memo = {}
        for alias, xml in xml_dict.items():
            if xml not in memo:
                memo[xml] = self._render(xml)
            self[alias] = memo[xml]

    def _render(self, xml:bytes) -> QIcon:
        """ Create a template with the given background color, render the XML in place, and convert it to an icon.
            Use the viewbox dimensions as pixel sizes. """
        svg = QSvgRenderer(xml)
        viewbox = svg.viewBox().size()
        im = QImage(viewbox, QImage.Format_ARGB32)
        im.fill(self._bg)
        with QPainter(im) as p:
            # Icons are small but important; set render hints for best quality.
            p.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
            svg.render(p)
        return QIcon(QPixmap.fromImage(im))


class ObjectTreeModel(QAbstractItemModel):
    """ A data model storing a tree of rows containing info about arbitrary Python objects. """

    _GRID_TYPE = List[List[TreeItem]]

    _row_model: RowModel                         # Formats items in each row with flags and roles.
    _eval_fn: Callable                           # Callable for evaluation of user input strings as Python code.
    _idx_to_grid: Dict[QModelIndex, _GRID_TYPE]  # Contains all expanded parent model indices mapped to grids of items.
    _idx_to_item: Dict[QModelIndex, TreeItem]    # Contains all generated model indices mapped to items.

    def __init__(self, tree:DebugTree):
        """ Create the index dictionaries and eval callback and fill out the root level of the tree. """
        super().__init__()
        root_data = tree.data()
        icon_data = tree.icons()
        icons = RenderedIconDict(icon_data)
        self._row_model = RowModel(icons)
        self._eval_fn = tree.eval
        self._idx_to_grid = defaultdict(list)
        root_idx = QModelIndex()
        root_item = KeyItem(None, root_data, {})
        self._idx_to_item = defaultdict(TreeItem, {root_idx: root_item})
        self.expand(root_idx)

    def index(self, row:int, col:int, parent:QModelIndex=None, *args) -> QModelIndex:
        try:
            r_item = self._idx_to_grid[parent][row][col]
            idx = self.createIndex(row, col, r_item)
            self._idx_to_item[idx] = r_item
            return idx
        except IndexError:
            return QModelIndex()

    def data(self, idx:QModelIndex, role:int=Qt.DisplayRole) -> Any:
        return self._idx_to_item[idx].role_data(role)

    def parent(self, idx:QModelIndex=None) -> QModelIndex:
        return self._idx_to_item[idx].parent

    def flags(self, idx:QModelIndex) -> Qt.ItemFlags:
        return self._idx_to_item[idx].flags

    def hasChildren(self, idx:QModelIndex=None, *args) -> bool:
        return self._idx_to_item[idx].child_data is not None

    def rowCount(self, idx:QModelIndex=None, *args) -> int:
        return len(self._idx_to_grid[idx])

    def columnCount(self, *args) -> int:
        return self._row_model.col_count()

    def headerData(self, section:int, orientation:int, role:int=None) -> Any:
        if orientation == Qt.Horizontal:
            return self._row_model.col_data(role, section)

    def setData(self, idx:QModelIndex, new_data:str, *args) -> bool:
        """ Attempt to change an object's value. Re-expand the parent on success, otherwise turn the item red. """
        # A blank field will not evaluate to anything; the user just clicked off of the field.
        if not new_data:
            return False
        # Either the value or the color will change, and either will affect the display, so return True.
        item = self._idx_to_item[idx]
        try:
            item.edit(new_data, eval_fn=self._eval_fn)
            self.expand(item.parent)
        except Exception:
            # Non-standard container classes could raise anything, so just ignore the specifics.
            # The item will return to the normal color after re-expansion.
            item.set_color((192, 0, 0))
        return True

    def expand(self, idx:QModelIndex) -> None:
        """ Add (or replace) all children on the item found at this index from internal object data. """
        rows = self._idx_to_grid[idx]
        if rows:
            # If there are existing child rows, get rid of them first.
            self.beginRemoveRows(idx, 0, len(rows))
            rows.clear()
            self.endRemoveRows()
        item = self._idx_to_item[idx]
        new_rows = self._row_model.expand(idx, item)
        if new_rows:
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
        model = ObjectTreeModel(*args)
        view = QTreeView(self)
        view.setFont(QFont("Segoe UI", 9))
        view.setUniformRowHeights(True)
        view.setModel(model)
        view.expanded.connect(model.expand)
        header = view.header()
        header.setDefaultSectionSize(120)
        header.resizeSection(0, 200)
        QVBoxLayout(self).addWidget(view)
