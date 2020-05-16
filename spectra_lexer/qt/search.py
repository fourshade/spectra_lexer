from typing import Callable, Dict, List

from PyQt5.QtWidgets import QCheckBox, QLineEdit

from .widgets import StringListView

MatchDict = Dict[str, List[str]]  # Ordered dict with strings matched in a search, each mapped to a list of values.


class _InputTextboxWrapper:

    def __init__(self, w_input:QLineEdit) -> None:
        self._w_input = w_input
        self.call_on_edit = w_input.textEdited.connect

    def set(self, value:str) -> None:
        return self._w_input.setText(value)

    def value(self) -> str:
        return self._w_input.text()

    def set_enabled(self, enabled:bool) -> None:
        self._w_input.setEnabled(enabled)


class _ListWrapper:

    def __init__(self, w_list:StringListView) -> None:
        self._w_list = w_list
        self.call_on_select = w_list.itemSelected.connect

    def set_items(self, items:List[str]) -> None:
        self._w_list.setItems(items)

    def select(self, value:str) -> None:
        self._w_list.selectByValue(value)

    def value(self) -> str:
        return self._w_list.selectedValue()

    def set_enabled(self, enabled:bool) -> None:
        self._w_list.setEnabled(enabled)


class _ModeCheckboxWrapper:

    def __init__(self, w_mode:QCheckBox) -> None:
        self._w_mode = w_mode
        self.call_on_toggle = w_mode.toggled.connect

    def __bool__(self) -> bool:
        return self._w_mode.isChecked()

    def set_enabled(self, enabled:bool) -> None:
        self._w_mode.setEnabled(enabled)


class SearchController:

    _MORE_TEXT = "(more...)"  # Text displayed as the final match, allowing the user to expand the search.

    def __init__(self, input_:_InputTextboxWrapper, matches:_ListWrapper, mappings:_ListWrapper,
                 strokes:_ModeCheckboxWrapper, regex:_ModeCheckboxWrapper) -> None:
        self._input = input_
        self._matches = matches
        self._mappings = mappings
        self._strokes = strokes
        self._regex = regex
        self._match_dict = {}
        self._last_page_count = 1
        self._on_search = lambda *_: None
        self._on_query = lambda *_: None
        strokes.call_on_toggle(self._send_search)
        regex.call_on_toggle(self._send_search)
        input_.call_on_edit(self._send_search)
        matches.call_on_select(self._match_selected)
        mappings.call_on_select(self._mapping_selected)
        self.get_mode_strokes = strokes.__bool__
        self.get_mode_regex = regex.__bool__
        self.update_input = input_.set

    def call_on_search(self, fn:Callable[[str, int], None]) -> None:
        self._on_search = fn

    def call_on_query(self, fn:Callable[..., None]) -> None:
        self._on_query = fn

    def _send_search(self, *_, page_count=1) -> None:
        """ Record the last number of pages requested and run a new search. """
        self._last_page_count = page_count
        self._on_search(self._input.value(), page_count)

    def _send_query(self, match:str, *mappings:str) -> None:
        """ Send a lexer query for one or more translations.
            The order of lexer parameters must be reversed for strokes mode. """
        translations = [([match, m] if self._strokes else [m, match]) for m in mappings]
        self._on_query(*translations)

    def _match_selected(self, match:str) -> None:
        """ If the user clicked "more", search again with another page.
            Otherwise, update the mappings list with the items corresponding to <match> and pick the best one. """
        if match == self._MORE_TEXT:
            self._send_search(page_count=self._last_page_count + 1)
        elif match in self._match_dict:
            mappings = self._match_dict[match]
            self._mappings.set_items(mappings)
            if mappings:
                self._send_query(match, *mappings)

    def _mapping_selected(self, mapping:str) -> None:
        """ Select a <mapping> and send a lexer query for this specific translation. """
        match = self._matches.value()
        self._send_query(match, mapping)

    def update_results(self, matches:MatchDict, *, can_expand=False) -> None:
        """ Replace the current set of search results.
            If <can_expand> is True, add a final list item to allow search expansion.
            If there was only one match, select it automatically and proceed with a query. """
        self._match_dict = matches
        match_list = list(matches)
        if can_expand:
            match_list.append(self._MORE_TEXT)
        self._matches.set_items(match_list)
        self._mappings.set_items([])
        if len(match_list) == 1:
            match = match_list[0]
            self._matches.select(match)
            self._match_selected(match)

    def select_translation(self, keys:str, letters:str) -> None:
        """ Set the current selections to match the analyzed translation if possible. Do not send queries. """
        match, mapping = [keys, letters] if self._strokes else [letters, keys]
        if match in self._match_dict:
            mappings = self._match_dict[match]
            self._matches.select(match)
            self._mappings.set_items(mappings)
            self._mappings.select(mapping)

    def set_enabled(self, enabled:bool) -> None:
        """ Enable/disable all search widgets. Invalidate the current search results on disable. """
        if not enabled:
            self.update_results({})
        self._input.set_enabled(enabled)
        self._matches.set_enabled(enabled)
        self._mappings.set_enabled(enabled)
        self._strokes.set_enabled(enabled)
        self._regex.set_enabled(enabled)

    @classmethod
    def from_widgets(cls, w_input:QLineEdit, w_matches:StringListView, w_mappings:StringListView,
                     w_strokes:QCheckBox, w_regex:QCheckBox) -> "SearchController":
        input_ = _InputTextboxWrapper(w_input)
        matches = _ListWrapper(w_matches)
        mappings = _ListWrapper(w_mappings)
        strokes = _ModeCheckboxWrapper(w_strokes)
        regex = _ModeCheckboxWrapper(w_regex)
        return cls(input_, matches, mappings, strokes, regex)
