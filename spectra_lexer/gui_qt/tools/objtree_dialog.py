from itertools import islice
from typing import Callable, Iterable, List

from PyQt5.QtCore import Qt, QModelIndex
from PyQt5.QtGui import QColor, QFont, QStandardItem, QStandardItemModel
from PyQt5.QtWidgets import QTreeView, QVBoxLayout

from .dialog import ToolDialog
from spectra_lexer.gui_qt.svg import IconRenderer

# Default maximum number of child objects to show for each object.
CHILD_LIMIT = 200
# Font color for data items in immutable containers.
COLOR_UNEDITABLE = QColor(96, 64, 64)


class RowItem(QStandardItem):
    """ Basic tree item. """

    _children: Iterable[tuple]  # Iterable container that creates children on expansion.
    _original_data: str = ""  # Original value string set on first expansion.
    _edit_cb: Callable = None   # Callable to set a value on a container, or None if immutable.

    def __init__(self, *args, color=None, children=(), edit_cb=None):
        super().__init__(*args)
        if color is not None:
            self.setForeground(color)
        # If there are children, add a dummy item to make the row expandable.
        self._children = children
        if children:
            self.appendRow(QStandardItem("dummy"))
        # If the item is editable, there will be a callback. Save the original data.
        self._edit_cb = edit_cb
        if edit_cb is None:
            self.setEditable(False)
        else:
            self._original_data = self.data(Qt.DisplayRole)

    def get_children(self) -> Iterable[tuple]:
        return self._children

    def write_value(self) -> bool:
        """ Attempt to change the underlying object to the current value by editing its container. """
        try:
            # Since only strings can be entered, we must evaluate them as Python expressions.
            # Any exception is possible; just abort if one occurs. Return True on success.
            self._edit_cb(eval(self.data(Qt.DisplayRole)))
            return True
        except Exception:
            # If the current value was not a valid Python expression or editing failed another way, reset it.
            self.setData(self._original_data, Qt.DisplayRole)
            return False


def create_row(key:object, obj:object, children:Iterable[tuple], edit_cb:Callable,
               irenderer:Callable, tfinder:Callable, vfinder:Callable) -> List[RowItem]:
    color = COLOR_UNEDITABLE if edit_cb is None else None
    # Column 0: the primary tree item with the key. Only it has an icon.
    primary = RowItem(irenderer(obj), str(key), color=color, children=children)
    # Column 1: contains the type of object and/or item count. Has a tooltip detailing the MRO.
    t_item = RowItem(str(children), color=color)
    t_item.setToolTip(tfinder(obj))
    # Column 2: contains the string value of the object. The value may be edited if mutable.
    v_item = RowItem(vfinder(obj), color=color, edit_cb=edit_cb)
    return [primary, t_item, v_item]


class ObjectTreeModel(QStandardItemModel):

    _item_parsers: Iterable[Callable]  # Contains icons for each supported object type and a custom repr function.

    def __init__(self, root:Iterable[tuple], *item_parsers:Callable):
        """ Fill out the root level of the tree and set the value edit callback. """
        super().__init__()
        self._item_parsers = item_parsers
        self.setHorizontalHeaderLabels(["Name", "Type/Item Count", "Value"])
        self.itemChanged.connect(self.write)
        self._expand(self.invisibleRootItem(), root)

    def expand(self, idx:QModelIndex) -> None:
        """ Expand the row found at this index to show its children. """
        self._expand_row(self.itemFromIndex(idx))

    def write(self, item:RowItem) -> None:
        """ Attempt to change an object's value. Re-expand the parent row if successful. """
        if item.write_value():
            # parent() returns None for direct children of the root item. This must be explicitly overridden.
            self._expand_row(item.parent() or self.invisibleRootItem())

    def _expand_row(self, item:RowItem) -> None:
        self._expand(item, item.get_children())

    def _expand(self, item:QStandardItem, children:Iterable[tuple]) -> None:
        """ Replace all child rows on the item containing info about arbitrary Python objects. """
        item.removeRows(0, item.rowCount())
        for args in islice(children, CHILD_LIMIT):
            item.appendRow(create_row(*args, *self._item_parsers))


class ObjectTreeView(QTreeView):

    def __init__(self, parent:ToolDialog, *, root:Iterable[tuple], xml_string:str,
                 ifinder:Callable, tfinder:Callable, vfinder:Callable):
        """ Create the constructors and item model. """
        super().__init__(parent)
        self.setFont(QFont("Segoe UI", 9))
        model = ObjectTreeModel(root, IconRenderer(xml_string, ifinder), tfinder, vfinder)
        self.setModel(model)
        # Format the header and connect the expansion signal.
        self.header().setDefaultSectionSize(120)
        self.header().resizeSection(0, 200)
        self.expanded.connect(model.expand)


class ObjectTreeDialog(ToolDialog):
    """ Qt tree dialog window object. """

    TITLE = "Python Object Tree View"
    SIZE = (600, 450)

    def make_layout(self, resources:dict) -> None:
        """ Create the layout and tree widget. """
        QVBoxLayout(self).addWidget(ObjectTreeView(self, **resources))
