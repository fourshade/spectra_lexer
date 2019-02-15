from functools import partial
from typing import List

from PyQt5.QtWidgets import QCheckBox, QLineEdit, QWidget

from spectra_lexer import Component, on
from spectra_lexer.gui_qt.search.search_list_widget import SearchListWidget


class GUIQtSearch(Component):
    """ GUI operations class for finding strokes and translations that are similar to one another. """

    ROLE = "gui_search"

    input_textbox: QLineEdit        # Input box for the user to enter a search string.
    match_list: SearchListWidget    # List box to show the direct matches for the user's search.
    mapping_list: SearchListWidget  # List box to show the mappings of a selection in the match list.
    strokes_chkbox: QCheckBox       # Check box to determine whether to use word or stroke search.
    regex_chkbox: QCheckBox         # Check box to determine whether to use prefix or regex search.

    def __init__(self, *widgets:QWidget):
        super().__init__()
        self.input_textbox, self.match_list, self.mapping_list, self.strokes_chkbox, self.regex_chkbox = widgets

    @on("start")
    def start(self, **opts) -> None:
        """ Connect all Qt signals on engine start. """
        signals = {self.input_textbox.textEdited:    "search_input",
                   self.match_list.itemSelected:     "search_choose_match",
                   self.mapping_list.itemSelected:   "search_choose_mapping",
                   self.strokes_chkbox.toggled:      "search_mode_strokes",
                   self.regex_chkbox.toggled:        "search_mode_regex"}
        for signal, cmd_key in signals.items():
            signal.connect(partial(self.engine_call, cmd_key))

    @on("new_search_state")
    def set_enabled(self, enabled:bool) -> None:
        """ Set up widgets and enable/disable searching based on whether or not a new search dict is empty. """
        self.input_textbox.clear()
        self.input_textbox.setPlaceholderText("Search..." if enabled else "No dictionaries.")
        self.match_list.clear()
        self.mapping_list.clear()
        self.strokes_chkbox.setChecked(False)
        self.regex_chkbox.setChecked(False)
        for w in (self.input_textbox, self.match_list, self.mapping_list,
                  self.strokes_chkbox, self.regex_chkbox):
            w.setEnabled(enabled)

    @on("new_search_matches")
    def set_matches(self, matches:List[str], selection:str=None) -> None:
        """ Update the upper list's contents and/or string selection. """
        self.match_list.set_items(matches)
        if selection is not None:
            self.match_list.select(selection)

    @on("new_search_mappings")
    def set_mappings(self, mappings:List[str], selection:str=None) -> None:
        """ Update the lower list's contents and/or string selection. """
        self.mapping_list.set_items(mappings)
        if selection is not None:
            self.mapping_list.select(selection)
