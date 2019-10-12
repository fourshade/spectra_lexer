from collections import defaultdict
from itertools import islice
from typing import Any, Callable, Iterable, Iterator

from PyQt5.QtCore import QAbstractItemModel, QModelIndex, QSize, Qt
from PyQt5.QtGui import QColor, QFont, QIcon, QImage, QPainter, QPixmap
from PyQt5.QtSvg import QSvgRenderer
from PyQt5.QtWidgets import QTreeView, QVBoxLayout

from .dialog import ToolDialog

from spectra_lexer.debug import DebugDataFactory, DebugData, package


class BaseItem:
    """ Abstract class for a single item in the tree. Contains model data in attributes and role data in the dict. """

    HEADING = "UNDEFINED"  # Heading that appears above this item type's column.

    def __init__(self, parent:QModelIndex=None) -> None:
        self._parent = parent  # Model index of the direct parent of this item (None for the root).
        self._roles = {}       # Contains all display data for this item indexed by Qt roles (really ints).
        self._edit_cb = None   # Callback to edit the value of this item, or None if not editable.
        self._child_iter = ()  # Iterable to produce child rows.

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
            self._set_color(192, 0, 0)
            return False

    def update(self, data:DebugData, *args) -> None:
        """ Update attributes and Qt display roles from a data structure. """
        raise NotImplementedError

    def _set_text(self, text:str) -> None:
        self._roles[Qt.DisplayRole] = text

    def _set_color(self, r:int, g:int, b:int) -> None:
        self._roles[Qt.ForegroundRole] = QColor(r, g, b)

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
        self._set_color(*data.color)
        self._set_text(data.key_text)
        self._set_tooltip(data.key_tooltip)
        self._set_edit_cb(data.key_edit)
        self._set_children(data)
        self._set_icon(icon)


class TypeItem(BaseItem):
    """ Column 1 contains the type of object, item count, and/or a tooltip detailing the MRO. """

    HEADING = "Type/Item Count"

    def update(self, data:DebugData, *args) -> None:
        self._set_color(*data.color)
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
        self._set_color(*data.color)
        self._set_text(data.value_text)
        self._set_tooltip(data.value_tooltip)
        self._set_edit_cb(data.value_edit)


class IconRenderer:
    """ Renders SVG bytes data on transparent bitmap images and caches the results. """

    # Icons are small but important. Use these render hints for best quality.
    _RENDER_HINTS = QPainter.Antialiasing | QPainter.SmoothPixmapTransform
    _TRANSPARENT_WHITE = QColor(255, 255, 255, 0)  # Transparent background color for icon rendering.

    def __init__(self) -> None:
        self._rendered = {}  # Cache of icons already rendered, keyed by the XML that generated it.

    def render(self, xml:bytes) -> QIcon:
        """ If we have the XML rendered, return the icon from the cache. Otherwise, render and cache it first. """
        if xml not in self._rendered:
            self._rendered[xml] = self._render(xml)
        return self._rendered[xml]

    def _render(self, xml:bytes) -> QIcon:
        """ Create a template with a transparent background, render the XML in place, and convert it to an icon.
            Use the viewbox dimensions as pixel sizes. """
        svg = QSvgRenderer(xml)
        viewbox = svg.viewBox().size()
        im = QImage(viewbox, QImage.Format_ARGB32)
        im.fill(self._TRANSPARENT_WHITE)
        with QPainter(im) as p:
            p.setRenderHints(self._RENDER_HINTS)
            svg.render(p)
        return QIcon(QPixmap.fromImage(im))


class ObjectTreeItemModel(QAbstractItemModel):
    """ A data model storing a tree of rows containing info about arbitrary Python objects. """

    COL_TYPES = [KeyItem, TypeItem, ValueItem]  # Determines what columns appear in the tree.
    _ROOT_IDX = QModelIndex()  # Sentinel value for the index of the root item.
    _HEADER_HEIGHT = 25        # Height of column headers in pixels.

    def __init__(self, icons:IconRenderer, root_item:BaseItem, child_limit:int=200) -> None:
        super().__init__()
        self._icons = icons              # Contains pre-rendered icons corresponding to data types.
        self._child_limit = child_limit  # Maximum number of child object rows to show for each object.
        self._idx_to_item = {self._ROOT_IDX: root_item}  # Contains model indices mapped to tree items.
        self._idx_to_children = defaultdict(list)        # Contains model indices mapped to grids of their children.

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
        return len(self.COL_TYPES)

    def headerData(self, section:int, orientation:int, role:int=None) -> Any:
        """ Return captions or height for the header at the top of the window (or None for other roles). """
        if orientation == Qt.Horizontal:
            if role == Qt.DisplayRole:
                return self.COL_TYPES[section].HEADING
            if role == Qt.SizeHintRole:
                return QSize(0, self._HEADER_HEIGHT)

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
        """ Add (or replace) all children on the item found at this index from internal object data. """
        child_rows = self._idx_to_children[idx]
        if child_rows:
            # If there are existing child rows, get rid of them first.
            self.beginRemoveRows(idx, 0, len(child_rows))
            child_rows.clear()
            self.endRemoveRows()
        # Generate rows of object debug data by iterating over the parent item up to a limit using islice.
        item = self._idx_to_item[idx]
        data_rows = list(islice(item, self._child_limit))
        # Create and add rows of tree items from the raw data.
        self.beginInsertRows(idx, 0, len(data_rows))
        for data in data_rows:
            icon_xml = data.icon_data
            icon = self._icons.render(icon_xml) if icon_xml else None
            new_row = [cls(idx) for cls in self.COL_TYPES]
            for item in new_row:
                item.update(data, icon)
            child_rows.append(new_row)
        self.endInsertRows()


class ObjectTreeDialog(ToolDialog):
    """ Qt tree dialog window object. """

    title = "Python Object Tree View"
    width = 600
    height = 450

    def setup(self, debug_vars:dict) -> None:
        """ Create the item model by putting together debug data structures and a row model.
            Create the tree widget with the item model, connect the expansion signal, and format the header. """
        debug_vars["modules"] = package.modules()
        factory = DebugDataFactory()
        factory.load_icons()
        root_data = factory.generate(debug_vars)
        root_item = KeyItem()
        root_item.update(root_data)
        qicons = IconRenderer()
        item_model = ObjectTreeItemModel(qicons, root_item)
        item_model.expand()
        view = self._make_tree_view()
        view.setModel(item_model)
        view.expanded.connect(item_model.expand)
        layout = QVBoxLayout(self)
        layout.addWidget(view)

    def _make_tree_view(self) -> QTreeView:
        view = QTreeView(self)
        view.setFont(QFont("Segoe UI", 9))
        view.setUniformRowHeights(True)
        header = view.header()
        header.setDefaultSectionSize(120)
        header.resizeSection(0, 200)
        return view
