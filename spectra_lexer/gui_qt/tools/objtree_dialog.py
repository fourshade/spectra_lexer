from functools import partial
from itertools import islice
from typing import Callable, Iterable

from PyQt5.QtCore import Qt, QModelIndex
from PyQt5.QtGui import QColor, QFont, QStandardItem, QStandardItemModel
from PyQt5.QtWidgets import QTreeView, QVBoxLayout

from .dialog import ToolDialog
from spectra_lexer.gui_qt.svg import IconRenderer

# Default maximum number of child objects to show for each object.
CHILD_LIMIT = 200
# Font color for data items in immutable containers.
COLOR_UNEDITABLE = QColor(96, 64, 64)


class _Item(QStandardItem):
    """ Basic tree item. """

    def __init__(self, edit_cb:Callable, *args):
        super().__init__(*args)
        self.setEditable(False)
        if edit_cb is None:
            self.setForeground(COLOR_UNEDITABLE)


class KeyItem(_Item):
    """ Tree item for showing an object's name/key. May be expanded if the object has contents. """

    children: Iterable[tuple]  # Iterable container that creates children on expansion.

    def __init__(self, ifinder:Callable, key, obj, children, edit_cb):
        """ Column 0: the primary tree item with the key. Only it has an icon. """
        super().__init__(edit_cb, ifinder(obj), str(key))
        self.children = children
        # If there are children, add a dummy item to make the row expandable.
        if children:
            self.appendRow(QStandardItem("dummy"))


class TypeItem(_Item):
    """ Basic tree item for showing an object's type. """

    def __init__(self, tfinder:Callable, key, obj, children, edit_cb):
        """ Column 1: contains the type of object and/or item count. Has a tooltip detailing the MRO. """
        super().__init__(edit_cb, str(children))
        self.setToolTip(tfinder(obj))


class ValueItem(_Item):
    """ Tree item for showing an object's value. The value may be edited if mutable. """

    _original_data: str   # Original value string set on first expansion.
    _edit_cb: Callable    # Callable to set a value on a container, or None if immutable.

    def __init__(self, vfinder:Callable, key, obj, children, edit_cb):
        """ Column 2: contains the string value of the object. Must be resettable to original value on creation. """
        s = self._original_data = vfinder(obj)
        super().__init__(edit_cb, s)
        self._edit_cb = edit_cb
        self.setEditable(bool(edit_cb))

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


class ObjectTreeView(QTreeView):

    _item_constructors: list  # Contains icons for each supported object type and a custom repr function.

    def __init__(self, parent, *, root:Iterable[tuple], ifinder:Callable, tfinder:Callable, vfinder:Callable):
        """ Create the constructors and item model and set the value edit callback. """
        super().__init__(parent)
        self._item_constructors = [partial(KeyItem, ifinder(IconRenderer)),
                                   partial(TypeItem, tfinder),
                                   partial(ValueItem, vfinder)]
        self.setFont(QFont("Segoe UI", 9))
        model = QStandardItemModel()
        model.setHorizontalHeaderLabels(["Name", "Type/Item Count", "Value"])
        model.itemChanged.connect(self.write)
        # Fill out the root level of the tree by populating the existing root item.
        r_item = model.invisibleRootItem()
        r_item.children = root
        self._expand(r_item)
        self.setModel(model)
        # Format the header and connect the expansion signal.
        self.header().setDefaultSectionSize(120)
        self.header().resizeSection(0, 200)
        self.expanded.connect(self.expand)

    def expand(self, idx:QModelIndex) -> None:
        """ Expand the item found at this index to show its children. """
        self._expand(self.model().itemFromIndex(idx))

    def write(self, item:ValueItem) -> None:
        """ Attempt to change an object's value. Re-expand the parent item if successful. """
        if item.write_value():
            # parent() returns None for direct children of the root item. This must be explicitly overridden.
            self._expand(item.parent() or self.model().invisibleRootItem())

    def _expand(self, item:KeyItem) -> None:
        """ Replace all child rows on the item containing info about arbitrary Python objects. """
        item.removeRows(0, item.rowCount())
        for args in islice(item.children, CHILD_LIMIT):
            item.appendRow([c(*args) for c in self._item_constructors])


class ObjectTreeDialog(ToolDialog):
    """ Qt tree dialog window object. """

    TITLE = "Python Object Tree View"
    SIZE = (600, 450)

    def make_layout(self, resources:dict) -> None:
        """ Create the layout and tree widget. """
        QVBoxLayout(self).addWidget(ObjectTreeView(self, **resources))
