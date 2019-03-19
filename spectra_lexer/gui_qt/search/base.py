from functools import partial

from PyQt5.QtWidgets import QCheckBox, QLineEdit, QWidget

from .search_list_widget import SearchListWidget
from spectra_lexer import Component
from spectra_lexer.utils import delegate_to


class GUIQtSearchPanel(Component):
    """ GUI operations class for finding strokes and translations that are similar to one another. """

    widgets: list                 # List of all search widgets for group operations.
    w_input: QLineEdit            # Input box for the user to enter a search string.
    w_matches: SearchListWidget   # List box to show the direct matches for the user's search.
    w_mappings: SearchListWidget  # List box to show the mappings of a selection in the match list.
    w_chk_strokes: QCheckBox      # Check box to determine whether to use word or stroke search.
    w_chk_regex: QCheckBox        # Check box to determine whether to use prefix or regex search.

    @on("new_gui_search")
    def new_gui(self, *widgets:QWidget) -> None:
        """ Save the required widgets and connect all Qt signals on engine start. """
        self.widgets = list(widgets)
        self.w_input, self.w_matches, self.w_mappings, self.w_chk_strokes, self.w_chk_regex = widgets
        signals = {self.w_input.textEdited:      "search_input",
                   self.w_matches.itemSelected:  "search_choose_match",
                   self.w_mappings.itemSelected: "search_choose_mapping",
                   self.w_chk_strokes.toggled:   "search_mode_strokes",
                   self.w_chk_regex.toggled:     "search_mode_regex"}
        for signal, cmd_key in signals.items():
            signal.connect(partial(self.engine_call, cmd_key))

    @on("gui_set_enabled")
    def set_enabled(self, enabled:bool) -> None:
        """ Enable/disable all search widgets. """
        self.w_input.clear()
        self.w_input.setPlaceholderText("Search..." if enabled else "No dictionaries.")
        self.w_matches.clear()
        self.w_mappings.clear()
        for w in self.widgets:
            w.setEnabled(enabled)

    set_input = on("new_search_input")(delegate_to("w_input.setText"))

    set_matches = on("new_search_match_list")(delegate_to("w_matches.set_items"))
    select_matches = on("new_search_match_selection")(delegate_to("w_matches.select"))

    set_mappings = on("new_search_mapping_list")(delegate_to("w_mappings.set_items"))
    select_mappings = on("new_search_mapping_selection")(delegate_to("w_mappings.select"))
