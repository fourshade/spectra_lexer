from typing import List, Union

from PyQt5.QtCore import pyqtSignal, QItemSelection, QItemSelectionModel, QStringListModel, Qt
from PyQt5.QtWidgets import QListView


class SearchListWidget(QListView):
    """ Simple QListView extension with strings that sends a signal when the selection has changed. """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setModel(QStringListModel([]))

    def clear(self) -> None:
        self.model().setStringList([])

    def set_items(self, s_list:List[str]) -> None:
        self.model().setStringList(s_list)

    def select(self, key:Union[int, str]) -> None:
        """ Programmatically select a specific item by index or first instance.
            Suppress signals to keep from tripping the selectionChanged event. """
        if isinstance(key, str):
            # The item *should* always exist, but if it doesn't, do nothing.
            try:
                key = self.model().stringList().index(key)
            except ValueError:
                return
        idx = self.model().index(key, 0)
        self.blockSignals(True)
        self.selectionModel().select(idx, QItemSelectionModel.SelectCurrent)
        self.blockSignals(False)

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
