from typing import Callable

from PyQt5.QtCore import QObject
from PyQt5.QtWidgets import QCheckBox, QLineEdit

from .widgets import StringListView


class SearchController(QObject):

    def __init__(self, w_input:QLineEdit, w_matches:StringListView, w_mappings:StringListView,
                 w_strokes:QCheckBox, w_regex:QCheckBox) -> None:
        super().__init__()
        self._w_input = w_input
        self._w_matches = w_matches
        self._w_mappings = w_mappings
        self._w_strokes = w_strokes
        self._w_regex = w_regex
        # List of all GUI input events that can result in a call to a steno engine action.
        self._events = [(w_strokes.toggled, "Search"),
                        (w_regex.toggled, "Search"),
                        (w_input.textEdited, "Search"),
                        (w_matches.itemSelected, "Lookup"),
                        (w_mappings.itemSelected, "Select")]
        # Dict of all possible GUI methods to call when a particular part of the state changes.
        self._methods = {"input_text":       w_input.setText,
                         "matches":          w_matches.setItems,
                         "match_selected":   w_matches.selectByValue,
                         "mappings":         w_mappings.setItems,
                         "mapping_selected": w_mappings.selectByValue}

    def get_state(self) -> dict:
        """ Return all GUI state values that may be needed by the steno engine. """
        return {"search_mode_strokes": self._w_strokes.isChecked(),
                "search_mode_regex": self._w_regex.isChecked(),
                "input_text": self._w_input.text(),
                "match_selected": self._w_matches.selectedValue(),
                "mapping_selected": self._w_mappings.selectedValue()}

    def connect(self, action_fn:Callable[[str], None]) -> None:
        """ Connect all input signals to the function with their corresponding action. """
        for signal, action_str in self._events:
            signal.connect(lambda *args, action=action_str: action_fn(action))

    def update(self, state:dict) -> None:
        """ For every state variable, call the corresponding GUI update method if one exists. """
        for k in self._methods:
            if k in state:
                self._methods[k](state[k])

    def set_enabled(self, enabled:bool) -> None:
        """ Enable/disable all search widgets. Leave the content intact. """
        self._w_input.setEnabled(enabled)
        self._w_matches.setEnabled(enabled)
        self._w_mappings.setEnabled(enabled)
        self._w_strokes.setEnabled(enabled)
        self._w_regex.setEnabled(enabled)
