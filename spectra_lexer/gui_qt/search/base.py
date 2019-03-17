from functools import partial

from PyQt5.QtWidgets import QCheckBox, QLineEdit, QWidget

from .search_list_widget import SearchListWidget
from spectra_lexer import Component
from spectra_lexer.utils import delegate_to


class GUIQtSearchPanel(Component):
    """ GUI operations class for finding strokes and translations that are similar to one another. """

    input_textbox: QLineEdit        # Input box for the user to enter a search string.
    match_list: SearchListWidget    # List box to show the direct matches for the user's search.
    mapping_list: SearchListWidget  # List box to show the mappings of a selection in the match list.
    strokes_chk: QCheckBox          # Check box to determine whether to use word or stroke search.
    regex_chk: QCheckBox            # Check box to determine whether to use prefix or regex search.

    @on("new_gui_search")
    def new_gui(self, *widgets:QWidget) -> None:
        """ Save the required widgets and connect all Qt signals on engine start. """
        self.input_textbox, self.match_list, self.mapping_list, self.strokes_chk, self.regex_chk = widgets
        signals = {self.input_textbox.textEdited:    "search_input",
                   self.match_list.itemSelected:     "search_choose_match",
                   self.mapping_list.itemSelected:   "search_choose_mapping",
                   self.strokes_chk.toggled:         "search_mode_strokes",
                   self.regex_chk.toggled:           "search_mode_regex"}
        for signal, cmd_key in signals.items():
            signal.connect(partial(self.engine_call, cmd_key))

    @on("new_search_state")
    def set_enabled(self, enabled:bool) -> None:
        """ Enable/disable all search widgets. """
        self.input_textbox.clear()
        self.input_textbox.setPlaceholderText("Search..." if enabled else "No dictionaries.")
        self.match_list.clear()
        self.mapping_list.clear()
        for w in (self.input_textbox, self.match_list, self.mapping_list, self.strokes_chk, self.regex_chk):
            w.setEnabled(enabled)

    set_matches = on("new_search_match_list")(delegate_to("match_list.set_items"))
    select_matches = on("new_search_match_selection")(delegate_to("match_list.select"))

    set_mappings = on("new_search_mapping_list")(delegate_to("mapping_list.set_items"))
    select_mappings = on("new_search_mapping_selection")(delegate_to("mapping_list.select"))
