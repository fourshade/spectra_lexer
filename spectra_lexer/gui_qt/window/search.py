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
        self.sig_strokes_mode = w_strokes.toggled
        self.sig_regex_mode = w_regex.toggled
        self.sig_edit_input = w_input.textEdited
        self.sig_select_match = w_matches.itemSelected
        self.sig_select_mapping = w_mappings.itemSelected
        self.set_input = w_input.setText
        self.set_matches = w_matches.setItems
        self.select_match = w_matches.selectByValue
        self.set_mappings = w_mappings.setItems
        self.select_mapping = w_mappings.selectByValue

    def set_enabled(self, enabled:bool) -> None:
        """ Enable/disable all search widgets. Leave the content intact. """
        self._w_input.setEnabled(enabled)
        self._w_matches.setEnabled(enabled)
        self._w_mappings.setEnabled(enabled)
        self._w_strokes.setEnabled(enabled)
        self._w_regex.setEnabled(enabled)
