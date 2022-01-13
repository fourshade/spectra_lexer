from typing import Iterable, Mapping, Sequence

from PyQt5.QtCore import pyqtSignal, QItemSelection, QObject, QStringListModel, Qt
from PyQt5.QtGui import QWheelEvent
from PyQt5.QtWidgets import QLineEdit, QListView

StringIter = Iterable[str]
StringSeq = Sequence[str]
SearchResults = Mapping[str, StringSeq]  # Ordered mapping of strings matched in a search to their possible values.

MORE_TEXT = "[more...]"  # Show this text as the last item in the match list to allow the user to expand the search.


class SearchListWidget(QListView):
    """ QListView extension with strings that sends a signal when the selection has changed. """

    itemSelected = pyqtSignal([str])  # Sent when a new list item is selected, with that item's string value.

    def __init__(self, *args, min_font_size=5, max_font_size=100) -> None:
        super().__init__(*args)
        self._min_font_size = min_font_size  # Minimum font size for list items in points.
        self._max_font_size = max_font_size  # Maximum font size for list items in points.
        self.setModel(QStringListModel([]))

    def setItems(self, str_iter:StringIter) -> None:
        """ Replace the list of items. This deselects every item, even ones that didn't change. """
        self.model().setStringList(str_iter)

    def selectByValue(self, value:str=None, *, center_selection=False) -> None:
        """ Programmatically select a specific item by value if it exists. If it doesn't, clear the selection.
            Suppress signals to keep from tripping the selectionChanged event. """
        self.blockSignals(True)
        try:
            model = self.model()
            list_idx = model.stringList().index(value)
            model_idx = model.index(list_idx, 0)
            sel_model = self.selectionModel()
            sel_model.select(model_idx, sel_model.SelectCurrent)
            if center_selection:
                # Put the selection as close as possible to the center of the viewing area.
                self.scrollTo(model_idx, self.PositionAtCenter)
        except ValueError:
            self.clearSelection()
        self.blockSignals(False)

    def selectedValue(self) -> str:
        """ Return the value of the first selected item (if any). """
        idxs = self.selectedIndexes()
        if not idxs:
            return ""
        return self.model().data(idxs[0], Qt.DisplayRole)

    def selectionChanged(self, selected:QItemSelection, deselected:QItemSelection) -> None:
        """ Send a signal on selection change with the first selected item (if any). """
        super().selectionChanged(selected, deselected)
        item_str = self.selectedValue()
        if item_str:
            self.itemSelected.emit(item_str)

    def wheelEvent(self, event:QWheelEvent) -> None:
        """ Change the font size if Ctrl is held down, otherwise scroll the list as usual. """
        if not event.modifiers() & Qt.ControlModifier:
            return super().wheelEvent(event)
        delta = event.angleDelta().y()
        sign = (delta // abs(delta)) if delta else 0
        font = self.font()
        new_size = font.pointSize() + sign
        if self._min_font_size <= new_size <= self._max_font_size:
            font.setPointSize(new_size)
            self.setFont(font)
        event.accept()


class SearchPanel(QObject):
    """ Controls the three main search widgets. """

    searchRequested = pyqtSignal([str, int])     # Emitted when a search operation is needed to refresh the lists.
    queryRequested = pyqtSignal([str, str])      # Emitted when a query should be made with a single translation.
    queryAllRequested = pyqtSignal([str, list])  # Emitted when a query should be made with multiple translations.

    def __init__(self, w_input:QLineEdit, w_matches:SearchListWidget, w_mappings:SearchListWidget) -> None:
        super().__init__(w_input)
        self._w_input = w_input
        self._w_matches = w_matches
        self._w_mappings = w_mappings
        self._matches = {}
        self._page_count = 1
        w_input.textEdited.connect(self.invalidate)
        w_matches.itemSelected.connect(self._on_user_select_match)
        w_mappings.itemSelected.connect(self._on_user_select_mapping)

    def _set_matches(self, matches:StringIter) -> None:
        self._w_matches.setItems(matches)

    def _set_mappings(self, mappings:StringIter) -> None:
        self._w_mappings.setItems(mappings)

    def _select_match(self, match:str) -> None:
        self._w_matches.selectByValue(match)

    def _select_mapping(self, mapping:str) -> None:
        self._w_mappings.selectByValue(mapping)

    def _send_search(self) -> None:
        """ Run a new search with the current input text and page count. """
        input_text = self._w_input.text()
        self.searchRequested.emit(input_text, self._page_count)

    def _new_search(self) -> None:
        """ Reset the page count and run a new search. """
        self._page_count = 1
        self._send_search()

    def _expanded_search(self) -> None:
        """ Add another page and run a new search. """
        self._page_count += 1
        self._send_search()

    def _on_user_select_match(self, match:str) -> None:
        """ If the user clicked "more", search again with another page.
            Otherwise, update the mappings list with the items corresponding to <match> and pick the best one. """
        if match == MORE_TEXT:
            self._expanded_search()
        elif match in self._matches:
            mappings = self._matches[match]
            self._set_mappings(mappings)
            if mappings:
                self.queryAllRequested.emit(match, [*mappings])

    def _on_user_select_mapping(self, mapping:str) -> None:
        """ When the user selects a <mapping>, send a lexer query for this specific translation. """
        if mapping:
            match = self._w_matches.selectedValue()
            self.queryRequested.emit(match, mapping)

    def invalidate(self, *_) -> None:
        """ Do a new search if something happens to invalidate the previous one. """
        self._new_search()

    def set_enabled(self, enabled:bool) -> None:
        """ Enable/disable all search widgets. """
        self._w_input.setEnabled(enabled)
        self._w_matches.setEnabled(enabled)
        self._w_mappings.setEnabled(enabled)

    def focus_input(self) -> None:
        """ Set focus to the search input box manually. """
        self._w_input.selectAll()
        self._w_input.setFocus(Qt.OtherFocusReason)

    def update_input(self, value:str) -> None:
        self._w_input.setText(value)

    def update_results(self, matches:SearchResults, *, can_expand=False) -> None:
        """ Replace the current set of search results. Add a special item to allow search expansion on click.
            If there was only one match, select it and proceed with a query as if the user had clicked it. """
        self._matches = matches
        match_list = list(matches)
        if can_expand:
            match_list.append(MORE_TEXT)
        self._set_matches(match_list)
        self._set_mappings([])
        if len(match_list) == 1:
            match = match_list[0]
            self._select_match(match)
            self._on_user_select_match(match)

    def select(self, match:str, mapping:str) -> None:
        """ Set the current selections to <match> and <mapping> if possible. Do not send queries. """
        if match in self._matches:
            mappings = self._matches[match]
            self._select_match(match)
            self._set_mappings(mappings)
            self._select_mapping(mapping)
