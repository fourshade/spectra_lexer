from typing import List

from PyQt5.QtCore import pyqtSignal, pyqtSlot, QItemSelection, QItemSelectionModel, QStringListModel, Qt
from PyQt5.QtWidgets import QListView


class InputListWidget(QListView):
    """ Simple QListView extension with strings that sends a signal when the selection has changed. """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setModel(QStringListModel([]))

    def clear(self) -> None:
        self.model().setStringList([])

    def set_items(self, s_list:List[str]) -> None:
        self.model().setStringList(s_list)

    def select(self, idx:int, suppress_event:bool=False) -> None:
        """ Programmatically select a specific item by index (w/ or w/out tripping the selectionChanged event). """
        sel_idx = self.model().index(idx, 0)
        if suppress_event:
            self.blockSignals(True)
        self.selectionModel().select(sel_idx, QItemSelectionModel.SelectCurrent)
        self.blockSignals(False)

    # Signals
    itemSelected = pyqtSignal([str])

    # Slots
    @pyqtSlot(QItemSelection, QItemSelection)
    def selectionChanged(self, selected:QItemSelection, deselected:QItemSelection) -> None:
        """ Send signal on selection change with the first selected item (if any). """
        super().selectionChanged(selected, deselected)
        idxs = selected.indexes()
        if idxs:
            item = self.model().data(idxs[0], Qt.DisplayRole)
            self.itemSelected.emit(item)
