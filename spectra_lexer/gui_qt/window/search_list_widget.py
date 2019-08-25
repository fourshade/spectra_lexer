from typing import List

from PyQt5.QtCore import pyqtSignal, QItemSelection, QItemSelectionModel, QStringListModel, Qt
from PyQt5.QtGui import QWheelEvent
from PyQt5.QtWidgets import QAbstractItemView, QListView


class SearchListWidget(QListView):
    """ Simple QListView extension with strings that sends a signal when the selection has changed. """

    def __init__(self, *args):
        super().__init__(*args)
        self.setModel(QStringListModel([]))

    def clear(self) -> None:
        self.model().setStringList([])

    def set_items(self, str_list:List[str]) -> None:
        self.model().setStringList(str_list)

    def select(self, key:str=None) -> None:
        """ Programmatically select a specific item by first instance (if it exists). If None, clear the selection.
            Scroll to put the item approximately in the middle of the page if possible.
            Suppress signals to keep from tripping the selectionChanged event. """
        self.blockSignals(True)
        try:
            self._change_selection(key)
        except ValueError:
            self.selectionModel().clearSelection()
        self.blockSignals(False)

    def _change_selection(self, key:str) -> None:
        """ Select an item by key and scroll to put it as close as possible to the center of the list. """
        key = self.model().stringList().index(key)
        idx = self.model().index(key, 0)
        self.selectionModel().select(idx, QItemSelectionModel.SelectCurrent)
        self.scrollTo(idx, QAbstractItemView.PositionAtCenter)

    def wheelEvent(self, event:QWheelEvent) -> None:
        """ Change the font size if Ctrl is held down, otherwise scroll the list as usual. """
        if not event.modifiers() & Qt.ControlModifier:
            return super().wheelEvent(event)
        delta = event.angleDelta().y()
        sign = delta // abs(delta)
        font = self.font()
        new_size = font.pointSize() + sign
        if 5 < new_size < 100:
            font.setPointSize(new_size)
            self.setFont(font)
        event.accept()

    # Signals
    itemSelected = pyqtSignal([str])

    def selectionChanged(self, selected:QItemSelection, deselected:QItemSelection) -> None:
        """ Send signal on selection change with the first selected item (if any). """
        super().selectionChanged(selected, deselected)
        idxs = selected.indexes()
        if idxs:
            item = self.model().data(idxs[0], Qt.DisplayRole)
            self.itemSelected.emit(item)
