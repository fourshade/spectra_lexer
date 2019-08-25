from typing import List

from PyQt5.QtCore import pyqtSignal, QItemSelection, QStringListModel, Qt
from PyQt5.QtGui import QWheelEvent
from PyQt5.QtWidgets import QListView


class SearchListWidget(QListView):
    """ Simple QListView extension with strings that sends a signal when the selection has changed. """

    VALID_FONT_SIZES = range(5, 100)  # Range of valid font sizes for list items in points.

    sig_select_item = pyqtSignal([str])  # Sent when a new list item is selected, with that item's string value.

    def __init__(self, *args) -> None:
        super().__init__(*args)
        self.setModel(QStringListModel([]))

    def set_items(self, str_list:List[str]) -> None:
        """ Replace the list of items. This deselects every item, even ones that didn't change. """
        self.model().setStringList(str_list)

    def select(self, key:str=None) -> None:
        """ Programmatically select a specific item by first instance (if it exists). If None, clear the selection.
            Suppress signals to keep from tripping the selectionChanged event. """
        self.blockSignals(True)
        try:
            self._change_selection(key)
        except ValueError:
            self.selectionModel().clearSelection()
        self.blockSignals(False)

    def _change_selection(self, key:str) -> None:
        """ Select an item by key and scroll to put it as close as possible to the center of the viewing area. """
        model = self.model()
        key = model.stringList().index(key)
        idx = model.index(key, 0)
        sel_model = self.selectionModel()
        sel_model.select(idx, sel_model.SelectCurrent)
        self.scrollTo(idx, self.PositionAtCenter)

    def wheelEvent(self, event:QWheelEvent) -> None:
        """ Change the font size if Ctrl is held down, otherwise scroll the list as usual. """
        if not event.modifiers() & Qt.ControlModifier:
            return super().wheelEvent(event)
        delta = event.angleDelta().y()
        sign = (delta // abs(delta)) if delta else 0
        font = self.font()
        new_size = font.pointSize() + sign
        if new_size in self.VALID_FONT_SIZES:
            font.setPointSize(new_size)
            self.setFont(font)
        event.accept()

    def selectionChanged(self, selected:QItemSelection, deselected:QItemSelection) -> None:
        """ Send a signal on selection change with the first selected item (if any). """
        super().selectionChanged(selected, deselected)
        idxs = selected.indexes()
        if idxs:
            item_str = self.model().data(idxs[0], Qt.DisplayRole)
            self.sig_select_item.emit(item_str)
