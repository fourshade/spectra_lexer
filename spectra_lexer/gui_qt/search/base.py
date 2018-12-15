from PyQt5.QtWidgets import QCheckBox, QLineEdit, QWidget

from spectra_lexer.gui_qt import GUIQtComponent
from spectra_lexer.gui_qt.search.search_list_widget import SearchListWidget


class GUIQtSearch(GUIQtComponent):

    w_input: QLineEdit            # Input box for the user to enter a search string.
    w_matches: SearchListWidget   # List box to show the direct matches for the user's search.
    w_mappings: SearchListWidget  # List box to show the mappings of a selection in the match list.
    w_type: QCheckBox             # Check box to determine whether to use word or stroke search.
    w_regex: QCheckBox            # Check box to determine whether to use prefix or regex search.

    def __init__(self, *widgets:QWidget):
        super().__init__()
        self.w_input, self.w_matches, self.w_mappings, self.w_type, self.w_regex = widgets

    def engine_commands(self) -> dict:
        """ Individual components must define the signals they respond to and the appropriate callbacks.
            Some commands have identical signatures to the Qt GUI methods; those can be passed directly. """
        return {**super().engine_commands(),
                "gui_reset_search":     self.reset_search,
                "gui_set_match_list":   self.w_matches.set_items,
                "gui_set_mapping_list": self.w_mappings.set_items,
                "gui_select_match":     self.w_matches.select,
                "gui_select_mapping":   self.w_mappings.select}

    def engine_slots(self) -> dict:
        """ Individual components must define the signals they respond to and the appropriate callbacks.
            Some commands have identical signatures to the Qt GUI methods; those can be passed directly. """
        return {**super().engine_slots(),
                self.w_input.textEdited:      "search_query",
                self.w_matches.itemSelected:  "search_choose_match",
                self.w_mappings.itemSelected: "search_choose_mapping",
                self.w_type.toggled:          "search_set_stroke_search",
                self.w_regex.toggled:         "search_set_regex_enabled"}

    def reset_search(self, enabled:bool) -> None:
        """ Reset all search widgets, then enable/disable them according to the argument. """
        self.w_input.clear()
        self.w_input.setPlaceholderText("Search..." if enabled else "No dictionaries.")
        self.w_matches.clear()
        self.w_mappings.clear()
        self.w_type.setChecked(False)
        self.w_regex.setChecked(False)
        for w in (self.w_input, self.w_matches, self.w_mappings,
                  self.w_type, self.w_regex):
            w.setEnabled(enabled)
