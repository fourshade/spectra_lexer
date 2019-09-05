from collections import defaultdict
from itertools import islice
from typing import Any, Callable, Dict, Iterable, Iterator, List, Optional, Tuple

from PyQt5.QtCore import QAbstractItemModel, QModelIndex, QSize, Qt
from PyQt5.QtGui import QColor, QFont, QIcon, QImage, QPainter, QPixmap
from PyQt5.QtSvg import QSvgRenderer
from PyQt5.QtWidgets import QTreeView, QVBoxLayout

from .dialog import ToolDialog
from spectra_lexer.debug import DebugDataFactory, DebugData, package


class BaseItem:
    """ Abstract class for a single item in the tree. Contains model data in attributes and role data in the dict. """

    HEADING: str = "UNDEFINED"  # Heading that appears above this item type's column.

    def __init__(self, parent:QModelIndex=None, *args) -> None:
        self._parent = parent  # Model index of the direct parent of this item (None for the root).
        self._roles = {}       # Contains all display data for this item indexed by Qt roles (really ints).
        self._edit_cb = None   # Callback to edit the value of this item, or None if not editable.
        self._child_iter = ()  # Iterable to produce child rows.
        if args:
            self.update(*args)

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
        return bool(self._child_iter)

    def __iter__(self) -> Iterator[DebugData]:
        return iter(self._child_iter)

    def edit(self, new_value:str) -> bool:
        """ Attempt to change the object's value. Return True on success. """
        try:
            self._edit_cb(new_value)
            return True
        except Exception:
            # Non-standard container classes could raise anything, so just ignore the specifics.
            # Turn the item red, The item will return to the normal color after re-expansion.
            self._set_color((192, 0, 0))
            return False

    def update(self, data:DebugData, *args) -> None:
        """ Update attributes and Qt display roles from a data structure. """
        raise NotImplementedError

    def _set_text(self, text:str) -> None:
        self._roles[Qt.DisplayRole] = text

    def _set_color(self, rgb:Tuple[int, int, int], _cache={}) -> None:
        """ Set an RGB color using a color generator with a default argument cache. """
        if rgb in _cache:
            color = _cache[rgb]
        else:
            color = _cache[rgb] = QColor(*rgb)
        self._roles[Qt.ForegroundRole] = color

    def _set_tooltip(self, tooltip:str) -> None:
        self._roles[Qt.ToolTipRole] = f'<pre>{tooltip}</pre>'

    def _set_edit_cb(self, edit:Callable[[str], None]) -> None:
        self._edit_cb = edit

    def _set_children(self, child_iter:Iterable[DebugData]) -> None:
        self._child_iter = child_iter

    def _set_icon(self, icon:QIcon) -> None:
        self._roles[Qt.DecorationRole] = icon


class KeyItem(BaseItem):
    """ Column 0 is the primary tree item with the key, icon, and children. Possible icons are based on type. """

    HEADING = "Name"

    def update(self, data:DebugData, icon:QIcon=None) -> None:
        self._set_color(data.color)
        self._set_text(data.key_text)
        self._set_tooltip(data.key_tooltip)
        self._set_edit_cb(data.key_edit)
        self._set_children(data)
        self._set_icon(icon)


class TypeItem(BaseItem):
    """ Column 1 contains the type of object, item count, and/or a tooltip detailing the MRO. """

    HEADING = "Type/Item Count"

    def update(self, data:DebugData, *args) -> None:
        self._set_color(data.color)
        text = data.type_text
        count = data.item_count
        if count is not None:
            text += f' - {count} item{"s" * (count != 1)}'
        self._set_text(text)
        self._set_tooltip(data.type_graph)


class ValueItem(BaseItem):
    """ Column 2 contains the string value of the object. It may be edited if mutable. """

    HEADING = "Value"

    def update(self, data:DebugData, *args) -> None:
        self._set_color(data.color)
        self._set_text(data.value_text)
        self._set_tooltip(data.value_tooltip)
        self._set_edit_cb(data.value_edit)


class IconRenderer:
    """ Renders SVG bytes data on transparent bitmap images. """

    def __init__(self, bg:QColor=QColor.fromRgb(255, 255, 255, 0)) -> None:
        self._bg = bg        # Background color for icon rendering; default is transparent white.
        self._rendered = {}  # Cache of icons already rendered, keyed by the XML that generated it.

    def _render(self, xml:bytes) -> None:
        """ Create a template with the given background color, render the XML in place, and convert it to an icon.
            Use the viewbox dimensions as pixel sizes. Store the icon in the cache when finished. """
        svg = QSvgRenderer(xml)
        viewbox = svg.viewBox().size()
        im = QImage(viewbox, QImage.Format_ARGB32)
        im.fill(self._bg)
        with QPainter(im) as p:
            # Icons are small but important; set render hints for best quality.
            p.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
            svg.render(p)
        icon = QIcon(QPixmap.fromImage(im))
        self._rendered[xml] = icon

    def render(self, xml:bytes) -> Optional[QIcon]:
        """ If we have the XML rendered, return the icon from memory. Otherwise, render it to the cache first. """
        if xml is not None:
            if xml not in self._rendered:
                self._render(xml)
            return self._rendered[xml]


class RowModel:
    """ Formats each tree item as a single row with a dict of parameters. """

    COL_TYPES = (KeyItem, TypeItem, ValueItem)  # Determines what columns appear in the tree.

    def __init__(self, icons:IconRenderer, child_limit:int=200) -> None:
        self._icons = icons              # Contains pre-rendered icons corresponding to data types.
        self._child_limit = child_limit  # Maximum number of child object rows to show for each object.

    def expand(self, item_idx:QModelIndex, item:BaseItem) -> List[List[BaseItem]]:
        """ Generate rows of tree items by iterating over the parent item up to a limit using islice. """
        return [self._make_row(item_idx, data) for data in islice(item, self._child_limit)]

    def _make_row(self, item_idx:QModelIndex, data:DebugData) -> List[BaseItem]:
        icon = self._icons.render(data.icon_data)
        return [cls(item_idx, data, icon) for cls in self.COL_TYPES]

    def col_count(self) -> int:
        return len(self.COL_TYPES)

    def col_data(self, role:int, section:int) -> Any:
        """ Return captions or height for the header at the top of the window (or None for other roles). """
        if role == Qt.DisplayRole:
            return self.COL_TYPES[section].HEADING
        if role == Qt.SizeHintRole:
            return QSize(0, 25)


class ObjectTreeItemModel(QAbstractItemModel):
    """ A data model storing a tree of rows containing info about arbitrary Python objects. """

    def __init__(self, row_model:RowModel, idx_to_item:Dict[QModelIndex, BaseItem]) -> None:
        """ Create the index dictionaries with the root level of the tree. """
        super().__init__()
        self._row_model = row_model            # Formats items in each row with flags and roles.
        self._idx_to_item = idx_to_item        # Contains all model indices mapped to items.
        self._idx_to_grid = defaultdict(list)  # Contains all parent model indices mapped to grids of their children.

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
        return self._idx_to_item[idx].parent()

    def flags(self, idx:QModelIndex) -> Qt.ItemFlags:
        return self._idx_to_item[idx].flags()

    def hasChildren(self, idx:QModelIndex=None, *args) -> bool:
        return self._idx_to_item[idx].has_children()

    def rowCount(self, idx:QModelIndex=None, *args) -> int:
        return len(self._idx_to_grid[idx])

    def columnCount(self, *args) -> int:
        return self._row_model.col_count()

    def headerData(self, section:int, orientation:int, role:int=None) -> Any:
        if orientation == Qt.Horizontal:
            return self._row_model.col_data(role, section)

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

    def setup(self, debug_vars:dict) -> None:
        """ Create the item model by putting together debug data structures and a row model.
            Create the tree widget with the item model, connect the expansion signal, and format the header. """
        self.setup_window("Python Object Tree View", 600, 450)
        debug_vars["modules"] = package.modules()
        factory = DebugDataFactory()
        factory.load_icons()
        root_data = factory.generate(debug_vars)
        root_item = KeyItem(None, root_data)
        qicons = IconRenderer()
        row_model = RowModel(qicons)
        root_idx = QModelIndex()
        idx_to_item = {root_idx: root_item}
        item_model = ObjectTreeItemModel(row_model, idx_to_item)
        item_model.expand(root_idx)
        view = QTreeView(self)
        view.setFont(QFont("Segoe UI", 9))
        view.setUniformRowHeights(True)
        view.setModel(item_model)
        view.expanded.connect(item_model.expand)
        header = view.header()
        header.setDefaultSectionSize(120)
        header.resizeSection(0, 200)
        QVBoxLayout(self).addWidget(view)
