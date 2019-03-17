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

    def set_items(self, s_list:List[str]) -> None:
        self.model().setStringList(s_list)

    def select(self, key:str) -> None:
        """ Programmatically select a specific item by first instance (if it exists).
            Scroll to put the item approximately in the middle of the page if possible.
            Suppress signals to keep from tripping the selectionChanged event. """
        try:
            key = self.model().stringList().index(key)
        except ValueError:
            return
        idx = self.model().index(key, 0)
        self.blockSignals(True)
        self._change_selection(idx)
        self.blockSignals(False)

    def _change_selection(self, idx:int) -> None:
        """ Select an item by index and scroll to put it as close as possible to the center of the list. """
        self.selectionModel().select(idx, QItemSelectionModel.SelectCurrent)
        self.scrollTo(idx, QAbstractItemView.PositionAtCenter)

    # Signals
    itemSelected = pyqtSignal([str])

    # Slots
    def selectionChanged(self, selected:QItemSelection, deselected:QItemSelection) -> None:
        """ Send signal on selection change with the first selected item (if any). """
        super().selectionChanged(selected, deselected)
        idxs = selected.indexes()
        if idxs:
            item = self.model().data(idxs[0], Qt.DisplayRole)
            self.itemSelected.emit(item)

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
