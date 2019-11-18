from typing import Callable, List

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QCheckBox, QLineEdit

from spectra_lexer.steno import SearchResults

from .widgets import StringListView


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

    def call_on_select(self, func:Callable) -> None:
        self._w_list.itemSelected.connect(func, Qt.QueuedConnection)

    def select(self, value:str) -> None:
        return self._w_list.selectByValue(value)

    def value(self) -> str:
        return self._w_list.selectedValue()

    def set_enabled(self, enabled:bool) -> None:
        self._w_list.setEnabled(enabled)


class _MatchListWrapper(_ListWrapper):

    def set_items(self, matches:List[str]) -> None:
        """ Set the match list and automatically select the match if there was only one. """
        self._w_list.setItems(matches)
        if len(matches) == 1:
            match = matches[0]
            self.select(match)
            self._w_list.itemSelected.emit(match)


class _MappingListWrapper(_ListWrapper):

    def set_items(self, mappings:List[str]) -> None:
        self._w_list.setItems(mappings)


class _ModeCheckboxWrapper:

    def __init__(self, w_mode:QCheckBox) -> None:
        self._w_mode = w_mode
        self.call_on_toggle = w_mode.toggled.connect

    def __bool__(self) -> bool:
        return self._w_mode.isChecked()

    def set_enabled(self, enabled:bool) -> None:
        self._w_mode.setEnabled(enabled)


class SearchController:

    def __init__(self, input_:_InputTextboxWrapper, matches:_MatchListWrapper, mappings:_MappingListWrapper,
                 strokes:_ModeCheckboxWrapper, regex:_ModeCheckboxWrapper) -> None:
        self._input = input_
        self._matches = matches
        self._mappings = mappings
        self._strokes = strokes
        self._regex = regex
        # List of all GUI input events that can result in a call to a steno engine action.
        self._events = [(strokes.call_on_toggle, "Search"),
                        (regex.call_on_toggle, "Search"),
                        (input_.call_on_edit, "Search"),
                        (matches.call_on_select, "Lookup"),
                        (mappings.call_on_select, "Select")]
        # Dict of all possible GUI methods to call when a particular part of the state changes.
        self._methods = {"input_text":       input_.set,
                         "matches":          matches.set_items,
                         "match_selected":   matches.select,
                         "mappings":         mappings.set_items,
                         "mapping_selected": mappings.select}

    def get_state(self) -> dict:
        """ Return all GUI state values that may be needed by the steno engine. """
        return {"search_mode_strokes": bool(self._strokes),
                "search_mode_regex": bool(self._regex),
                "input_text": self._input.value(),
                "match_selected": self._matches.value(),
                "mapping_selected": self._mappings.value()}

    def connect(self, action_fn:Callable[[str], None]) -> None:
        """ Connect all input callbacks to the function with their corresponding action. """
        for callback_set, action_str in self._events:
            callback_set(lambda *args, action=action_str: action_fn(action))

    def update(self, **state) -> None:
        """ For every state variable, call the corresponding GUI update method if one exists. """
        for k in self._methods:
            if k in state:
                self._methods[k](state[k])

    def set_enabled(self, enabled:bool) -> None:
        """ Enable/disable all search widgets. Leave the content intact. """
        self._input.set_enabled(enabled)
        self._matches.set_enabled(enabled)
        self._mappings.set_enabled(enabled)
        self._strokes.set_enabled(enabled)
        self._regex.set_enabled(enabled)

    @classmethod
    def from_widgets(cls, w_input:QLineEdit, w_matches:StringListView, w_mappings:StringListView,
                     w_strokes:QCheckBox, w_regex:QCheckBox):
        input_ = _InputTextboxWrapper(w_input)
        matches = _MatchListWrapper(w_matches)
        mappings = _MappingListWrapper(w_mappings)
        strokes = _ModeCheckboxWrapper(w_strokes)
        regex = _ModeCheckboxWrapper(w_regex)
        return cls(input_, matches, mappings, strokes, regex)
