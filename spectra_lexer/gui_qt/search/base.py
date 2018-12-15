from typing import Any

from PyQt5.QtWidgets import QCheckBox, QLineEdit, QWidget

from spectra_lexer import SpectraComponent
from spectra_lexer.gui_qt.search.search_list_widget import SearchListWidget

# Hard limit on the number of matches returned by a special search.
_MATCH_LIMIT = 100


class GUIQtSearch(SpectraComponent):
    """ GUI operations class for finding strokes and translations that are similar to one another. """

    input_textbox: QLineEdit        # Input box for the user to enter a search string.
    match_list: SearchListWidget    # List box to show the direct matches for the user's search.
    mapping_list: SearchListWidget  # List box to show the mappings of a selection in the match list.
    strokes_chkbox: QCheckBox       # Check box to determine whether to use word or stroke search.
    regex_chkbox: QCheckBox         # Check box to determine whether to use prefix or regex search.

    _last_match: str = ""  # Last search match selected by the user in the list.

    def __init__(self, *widgets:QWidget):
        super().__init__()
        self.input_textbox, self.match_list, self.mapping_list, self.strokes_chkbox, self.regex_chkbox = widgets
        self.input_textbox.textEdited.connect(self.on_search)
        self.match_list.itemSelected.connect(self.on_choose_match)
        self.mapping_list.itemSelected.connect(self.on_choose_mapping)
        self.strokes_chkbox.toggled.connect(self.on_search)
        self.regex_chkbox.toggled.connect(self.on_search)
        self.add_commands({"new_window":      self.on_new_window,
                           "new_search_dict": self.on_new_dict})

    def on_new_window(self) -> None:
        """ Enable searching only if there is a search dictionary loaded after initialization."""
        first_entry = self.engine_call("search_special", "", 1)
        self._clear_and_set_enabled(bool(first_entry))

    def on_new_dict(self, src_dict:dict) -> None:
        """ When a new dict comes along, enable/disable searching based on whether or not it is empty or None. """
        self._clear_and_set_enabled(bool(src_dict))

    def _clear_and_set_enabled(self, enabled:bool) -> None:
        """ Clear all search widgets, then enable/disable them according to the argument. """
        self.input_textbox.clear()
        self.input_textbox.setPlaceholderText("Search..." if enabled else "No dictionaries.")
        self.match_list.clear()
        self.mapping_list.clear()
        self.strokes_chkbox.setChecked(False)
        self.regex_chkbox.setChecked(False)
        for w in (self.input_textbox, self.match_list, self.mapping_list,
                  self.strokes_chkbox, self.regex_chkbox):
            w.setEnabled(enabled)

    def on_search(self, pattern:Any=None) -> None:
        """ Look up a pattern in the dictionary and populate the matches list. """
        if not isinstance(pattern, str):
            # If the argument is None or not a string, something other than the text box called this.
            # In that case, search for the previous text again (possibly with a new mode).
            pattern = self.input_textbox.text()
        # The mappings list is always invalidated when the matches list is updated, so clear it.
        self.mapping_list.clear()
        # If the text box is blank, a search would return the entire dictionary, so don't bother.
        if not pattern:
            self.match_list.clear()
            return
        # Choose the right type of search based on the mode flags, execute it, and show the list of results.
        matches = self.engine_call("search_special", pattern, _MATCH_LIMIT, self._mode_strokes, self._mode_regex)
        self.match_list.set_items(matches)
        # If there's only one match and it's new, select it and continue as if the user had done it.
        if len(matches) == 1 and matches[0] != self._last_match:
            self.match_list.select(0)
            self.on_choose_match(matches[0])

    def on_choose_match(self, match:str) -> None:
        """ When a match is chosen from the upper list, look up its mappings and display them in the lower list. """
        self._last_match = match
        mapping_or_list = self.engine_call("search_lookup", match, self._mode_strokes)
        if not mapping_or_list:
            return
        # We now have either a non-empty string (stroke mode) or a non-empty list of strings (word mode).
        # In either case, display the mapping results in list form and begin analysis.
        m_list = [mapping_or_list] if self._mode_strokes else mapping_or_list
        self.mapping_list.set_items(m_list)
        # With one mapping (either mode), it is a regular query with a defined stroke and word.
        if len(m_list) == 1:
            self.mapping_list.select(0)
            self.on_choose_mapping(m_list[0])
            return
        # If there is more than one mapping (only in word mode), make a lexer query to select the best one.
        assert not self._mode_strokes
        result = self.engine_call("new_query_product", m_list, [match])
        # Parse the rule's keys back into RTFCRE form and try to select that string in the list.
        keys = result.keys.inv_parse()
        self.mapping_list.select(keys)

    def on_choose_mapping(self, mapping:str) -> None:
        """ Make and send a lexer query based on the last selected match and this mapping (if non-empty). """
        match = self._last_match
        if not match or not mapping:
            return
        # The order of strokes/word depends on the mode.
        strokes, word = (match, mapping) if self._mode_strokes else (mapping, match)
        self.engine_call("new_query", strokes, word)

    @property
    def _mode_strokes(self) -> bool:
        return self.strokes_chkbox.isChecked()

    @property
    def _mode_regex(self) -> bool:
        return self.regex_chkbox.isChecked()
