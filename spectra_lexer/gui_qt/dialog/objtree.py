from collections import defaultdict
from itertools import islice
from typing import Any, Callable, Dict, Iterable, List, Optional

from PyQt5.QtCore import QAbstractItemModel, QModelIndex, QSize, Qt
from PyQt5.QtGui import QColor, QFont, QIcon, QImage, QPainter, QPixmap
from PyQt5.QtSvg import QSvgRenderer
from PyQt5.QtWidgets import QTreeView, QVBoxLayout

from .dialog import ToolDialog
from spectra_lexer.debug import DataFactory, DebugData, DebugIcons, package


class RenderedIcons:
    """ SVG icon dict that renders SVG bytes data on transparent bitmap images. """

    def __init__(self, xml_icons:DebugIcons, bg:QColor=QColor.fromRgb(255, 255, 255, 0)) -> None:
        self._xml_icons = xml_icons  # Original container of XML icon data.
        self._bg = bg                # Background color for icon rendering; default is transparent white.
        self._rendered = {}          # Cache of icons already rendered, keyed by the XML that generated it.

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

    def get(self, data:DebugData) -> Optional[QIcon]:
        """ Look up the best icon for the given data. Return None if no suitable icon is found.
            If we have the XML rendered, return the icon from memory. Otherwise, render it to the cache first. """
        xml = self._xml_icons.get_best(data)
        if xml is not None:
            if xml not in self._rendered:
                self._render(xml)
            return self._rendered[xml]


class BaseItem:
    """ Abstract class for a single item in the tree. Contains model data in attributes and role data in the dict. """

    HEADING: str = "UNDEFINED"  # Heading that appears above this item type's column.

    flags: Qt.ItemFlags = Qt.ItemIsSelectable | Qt.ItemIsEnabled  # Default item flags. Items are black and selectable.
    edit: Callable = None  # Callback to edit the value of this item, or None if not editable.
    child_data: Iterable[DebugData] = None  # Iterable to produce child rows, or None if there are no children.

    def __init__(self, parent:QModelIndex=None, *args) -> None:
        self._roles = {}      # Contains all display data for this item indexed by Qt roles (really ints).
        self.parent = parent  # Model index of the direct parent of this item (None for the root).
        if args:
            self.update(*args)

    def update(self, data:DebugData, *args) -> None:
        """ Update the item flags and Qt display roles from various pieces of data in a data structure. """
        raise NotImplementedError

    def role_data(self, role:int) -> Any:
        """ Return a role data item. Used heavily by the Qt item model. """
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

    def set_icon(self, icon:QIcon) -> None:
        self._roles[Qt.DecorationRole] = icon


class KeyItem(BaseItem):
    """ Column 0 is the primary tree item with the key and icon. Possible icons are based on type. """

    HEADING = "Name"

    def update(self, data:DebugData, icons:RenderedIcons=None) -> None:
        self.set_color(data.color)
        self.set_text(data.key_text)
        self.set_tooltip(data.key_tooltip)
        self.set_edit_cb(data.key_edit)
        self.child_data = data.child_data
        if icons is not None:
            icon = icons.get(data)
            self.set_icon(icon)


class TypeItem(BaseItem):
    """ Column 1 contains the type of object, item count, and/or a tooltip detailing the MRO. """

    HEADING = "Type/Item Count"

    def update(self, data:DebugData, *args) -> None:
        self.set_color(data.color)
        self.set_text(data.type_text, data.item_count)
        self.set_tooltip(data.type_graph)

    def set_text(self, text:str, item_count:int=None) -> None:
        if item_count is not None:
            text += f' - {item_count} item{"s" * (item_count != 1)}'
        super().set_text(text)


class ValueItem(BaseItem):
    """ Column 2 contains the string value of the object. It may be edited if mutable. """

    HEADING = "Value"

    def update(self, data:DebugData, *args) -> None:
        self.set_color(data.color)
        self.set_text(data.value_text)
        self.set_tooltip(data.value_tooltip)
        self.set_edit_cb(data.value_edit)


class RowModel:
    """ Formats each tree item as a single row with a dict of parameters. """

    COL_TYPES = (KeyItem, TypeItem, ValueItem)  # Determines what columns appear in the tree.

    def __init__(self, icons:RenderedIcons, child_limit:int=200) -> None:
        self._icons = icons              # Contains pre-rendered icons corresponding to data types.
        self._child_limit = child_limit  # Maximum number of child object rows to show for each object.

    def expand(self, item_idx:QModelIndex, item:BaseItem) -> List[List[BaseItem]]:
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

    def setData(self, idx:QModelIndex, new_value:str, *args) -> bool:
        """ Attempt to change an object's value. Re-expand the parent on success, otherwise turn the item red. """
        # A blank field will not evaluate to anything; the user just clicked off of the field.
        if not new_value:
            return False
        # Either the value or the color will change, and either will affect the display, so return True.
        item = self._idx_to_item[idx]
        try:
            item.edit(new_value)
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

    def setup(self, *args) -> None:
        """ Create the item model by putting together debug data structures and a row model with icons.
            Create the tree widget with the item model, connect the expansion signal, and format the header. """
        self.setup_window("Python Object Tree View", 600, 450)
        root_dict = package.with_modules(*args)
        root_data = DataFactory.generate(root_dict)
        root_item = KeyItem(None, root_data)
        xml_icons = DebugIcons()
        xml_icons.load()
        qicons = RenderedIcons(xml_icons)
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
