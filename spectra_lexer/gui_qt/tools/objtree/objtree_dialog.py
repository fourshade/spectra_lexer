from itertools import islice
from typing import Callable, Iterable

from PyQt5.QtCore import Qt, QModelIndex
from PyQt5.QtGui import QColor, QFont, QIcon, QStandardItem, QStandardItemModel
from PyQt5.QtWidgets import QTreeView, QVBoxLayout

from .icon import IconFinder
from .repr import NodeRepr
from spectra_lexer.gui_qt.tools.dialog import ToolDialog
from spectra_lexer.utils import memoize_one_arg

# Default maximum number of child objects to show for each object.
CHILD_LIMIT = 200
# Font color for data items in immutable containers.
COLOR_UNEDITABLE = QColor(96, 64, 64)


class _Item(QStandardItem):
    """ Basic tree item. """

    def __init__(self, *args, color:QColor=None, **kwargs):
        super().__init__(*args)
        self.setEditable(False)
        if color is not None:
            self.setForeground(color)


class KeyItem(_Item):
    """ Tree item for showing an object's name/key. May be expanded if the object has contents. """

    children: Iterable[tuple]  # Iterable container that creates children on expansion.

    def __init__(self, children:Iterable[tuple], key:object, icon:QIcon=None, **kwargs):
        """ If there are children, add a dummy item to make the row expandable. """
        super().__init__(icon, str(key), **kwargs)
        self.children = children
        if children:
            self.appendRow(QStandardItem("dummy"))


class TypeItem(_Item):
    """ Basic tree item for showing an object's type. """

    def __init__(self, children:Iterable[tuple], obj:object, **kwargs):
        super().__init__(str(children), **kwargs)
        self.setToolTip(_mro_listing(type(obj)))


@memoize_one_arg
def _mro_listing(tp:type) -> str:
    """ Return (and cache) a string representation of the type's MRO. """
    return "\n".join([("--" * i) + cls.__name__ for i, cls in enumerate(tp.__mro__[::-1])])


class ValueItem(_Item):
    """ Tree item for showing an object's value. The value may be edited if mutable. """

    main_parent: KeyItem  # Primary item parent. May be the root item.
    _original_data: str   # Original value string set on first expansion.
    _edit_cb: Callable    # Callable to set a value on a container, or None if immutable.

    def __init__(self, parent:KeyItem, edit_cb:Callable, repr_val:str, **kwargs):
        super().__init__(repr_val, **kwargs)
        self.main_parent = parent
        self._original_data = repr_val
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

    _get_icon: Callable       # Contains icons for each supported object type.
    _get_value_str: Callable  # Custom repr function for displaying node values.

    def __init__(self, parent, root_collection:Iterable[tuple], icon_dict:dict) -> None:
        """ Create the constructors and item model and set the value edit callback. """
        super().__init__(parent)
        self._get_icon = IconFinder(icon_dict).get_icon
        self._get_value_str = NodeRepr().repr
        self.setFont(QFont("Segoe UI", 9))
        model = QStandardItemModel()
        model.setHorizontalHeaderLabels(["Name", "Type/Item Count", "Value"])
        model.itemChanged.connect(self.write)
        # Fill out the root level of the tree by populating the existing root item.
        r_item = model.invisibleRootItem()
        r_item.children = root_collection
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
            self._expand(item.main_parent)

    def _expand(self, item:KeyItem) -> None:
        """ Replace all child rows on the item containing info about arbitrary Python objects. """
        item.removeRows(0, item.rowCount())
        for key, obj, children, edit_cb in islice(item.children, CHILD_LIMIT):
            # The first item is the primary tree item with the key (column 0). Only it has an icon.
            # The second item contains the type of object and/or item count (column 1).
            # The third item contains the string value of the object (column 2).
            kwargs = dict(parent=item, key=key, obj=obj, children=children, edit_cb=edit_cb,
                          icon=self._get_icon(obj), repr_val=self._get_value_str(obj))
            if edit_cb is None:
                kwargs["color"] = COLOR_UNEDITABLE
            item.appendRow([i_tp(**kwargs) for i_tp in (KeyItem, TypeItem, ValueItem)])


class ObjectTreeDialog(ToolDialog):
    """ Qt tree dialog window object. """

    TITLE = "Python Object Tree View"
    SIZE = (600, 450)

    def make_layout(self, *args) -> None:
        """ Create the layout and tree widget. """
        QVBoxLayout(self).addWidget(ObjectTreeView(self, *args))
