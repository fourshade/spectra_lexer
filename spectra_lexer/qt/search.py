from typing import Callable, Mapping, Sequence

from PyQt5.QtWidgets import QCheckBox, QLineEdit

from .widgets import StringListView

StringSeq = Sequence[str]
SearchResults = Mapping[str, StringSeq]  # Ordered mapping of strings matched in a search to their possible values.
SearchCallback = Callable[[str, int], None]
QueryCallback = Callable[[StringSeq, str], None]


class SearchPanel:
    """ Controls the three main search widgets. """

    _MORE_TEXT = "[more...]"  # Text displayed as the final match, allowing the user to expand the search.

    def __init__(self, w_input:QLineEdit, w_matches:StringListView, w_mappings:StringListView,
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

    def _send_query(self, match:str, mappings:StringSeq) -> None:
        """ Send a lexer query for one or more translations.
            The order of lexer parameters must be reversed for strokes mode.
            Currently, strokes can never have more than one mapping. """
        assert mappings
        if self.is_mode_strokes():
            self._call_query([match], mappings[0])
        else:
            self._call_query(mappings, match)

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
                self._send_query(match, mappings)

    def _on_user_select_mapping(self, mapping:str) -> None:
        """ When the user selects a <mapping>, send a lexer query for this specific translation. """
        if mapping:
            match = self._w_matches.selectedValue()
            self._send_query(match, [mapping])

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

    def clear_results(self) -> None:
        self.update_results({})

    def select_translation(self, keys:str, letters:str) -> None:
        """ Set the current selections to match the analyzed translation if possible. Do not send queries. """
        match, mapping = [keys, letters] if self.is_mode_strokes() else [letters, keys]
        if match in self._matches:
            mappings = self._matches[match]
            self._select_match(match)
            self._set_mappings(mappings)
            self._select_mapping(mapping)
