from typing import Callable, Iterable, Mapping, Sequence

from PyQt5.QtCore import pyqtSignal, QItemSelection, QStringListModel, Qt
from PyQt5.QtGui import QWheelEvent
from PyQt5.QtWidgets import QCheckBox, QLineEdit, QListView

StringSeq = Sequence[str]
SearchResults = Mapping[str, StringSeq]  # Ordered mapping of strings matched in a search to their possible values.
SearchCallback = Callable[[str, int], None]
QueryCallback = Callable[[str, StringSeq], None]


class SearchListWidget(QListView):
    """ QListView extension with strings that sends a signal when the selection has changed. """

    itemSelected = pyqtSignal([str])  # Sent when a new list item is selected, with that item's string value.

    def __init__(self, *args, min_font_size=5, max_font_size=100) -> None:
        super().__init__(*args)
        self._min_font_size = min_font_size  # Minimum font size for list items in points.
        self._max_font_size = max_font_size  # Maximum font size for list items in points.
        self.setModel(QStringListModel([]))

    def setItems(self, str_iter:Iterable[str]) -> None:
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


class SearchPanel:
    """ Controls the three main search widgets. """

    _MORE_TEXT = "[more...]"  # Text displayed as the final match, allowing the user to expand the search.

    def __init__(self, w_input:QLineEdit, w_matches:SearchListWidget, w_mappings:SearchListWidget,
                 w_strokes:QCheckBox, w_regex:QCheckBox) -> None:
        self._w_input = w_input
        self._w_matches = w_matches
        self._w_mappings = w_mappings
        self._w_strokes = w_strokes
        self._w_regex = w_regex
        self._matches = {}
        self._page_count = 1
        self._call_search = lambda *_: None
        self._call_query = lambda *_: None

    def _set_matches(self, matches:StringSeq) -> None:
        self._w_matches.setItems(matches)

    def _set_mappings(self, mappings:StringSeq) -> None:
        self._w_mappings.setItems(mappings)

    def _select_match(self, match:str) -> None:
        self._w_matches.selectByValue(match)

    def _select_mapping(self, mapping:str) -> None:
        self._w_mappings.selectByValue(mapping)

    def _send_search(self) -> None:
        """ Run a new search with the current input text and page count. """
        input_text = self._w_input.text()
        self._call_search(input_text, self._page_count)

    def _new_search(self) -> None:
        """ Reset the page count and run a new search. """
        self._page_count = 1
        self._send_search()

    def _expanded_search(self) -> None:
        """ Add another page and run a new search. """
        self._page_count += 1
        self._send_search()

    def _on_invalidate_search(self, *_) -> None:
        """ Do a new search on certain signals (disregard their arguments). """
        self._new_search()

    def _on_user_select_match(self, match:str) -> None:
        """ If the user clicked "more", search again with another page.
            Otherwise, update the mappings list with the items corresponding to <match> and pick the best one. """
        if match == self._MORE_TEXT:
            self._expanded_search()
        elif match in self._matches:
            mappings = self._matches[match]
            self._set_mappings(mappings)
            if mappings:
                self._call_query(match, mappings)

    def _on_user_select_mapping(self, mapping:str) -> None:
        """ When the user selects a <mapping>, send a lexer query for this specific translation. """
        if mapping:
            match = self._w_matches.selectedValue()
            self._call_query(match, [mapping])

    def connect_signals(self, call_search:SearchCallback, call_query:QueryCallback) -> None:
        """ Connect all Qt signals for user actions and set the callback functions. """
        self._call_search = call_search
        self._call_query = call_query
        self._w_strokes.toggled.connect(self._on_invalidate_search)
        self._w_regex.toggled.connect(self._on_invalidate_search)
        self._w_input.textEdited.connect(self._on_invalidate_search)
        self._w_matches.itemSelected.connect(self._on_user_select_match)
        self._w_mappings.itemSelected.connect(self._on_user_select_mapping)

    def is_mode_strokes(self) -> bool:
        return self._w_strokes.isChecked()

    def is_mode_regex(self) -> bool:
        return self._w_regex.isChecked()

    def set_enabled(self, enabled:bool) -> None:
        """ Enable/disable all search widgets. """
        self._w_input.setEnabled(enabled)
        self._w_matches.setEnabled(enabled)
        self._w_mappings.setEnabled(enabled)
        self._w_strokes.setEnabled(enabled)
        self._w_regex.setEnabled(enabled)

    def update_input(self, value:str) -> None:
        return self._w_input.setText(value)

    def update_results(self, matches:SearchResults) -> None:
        """ Replace the current set of search results.
            If there was only one match, select it and proceed with a query as if the user had clicked it. """
        self._matches = matches
        match_list = list(matches)
        self._set_matches(match_list)
        self._set_mappings([])
        if len(match_list) == 1:
            match = match_list[0]
            self._select_match(match)
            self._on_user_select_match(match)

    def select(self, match:str, mapping="") -> None:
        """ Set the current selections to <match> and <mapping> if possible. Do not send queries. """
        if match in self._matches:
            mappings = self._matches[match]
            self._select_match(match)
            self._set_mappings(mappings)
            self._select_mapping(mapping)
