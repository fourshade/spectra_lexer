from functools import partial

from spectra_lexer import Component
from spectra_lexer.utils import delegate_to


class GUIQtSearchPanel(Component):
    """ GUI operations class for finding strokes and translations that are similar to one another. """

    w_input = resource("gui:w_search_input",       desc="Input box for the user to enter a search string.")
    w_matches = resource("gui:w_search_matches",   desc="List box to show the matches for the user's search.")
    w_mappings = resource("gui:w_search_mappings", desc="List box to show the mappings of a match selection.")
    w_strokes = resource("gui:w_search_type",      desc="Check box: False = word search, True = stroke search.")
    w_regex = resource("gui:w_search_regex",       desc="Check box: False = prefix search, True = regex search.")

    @on("load_gui")
    def load(self) -> None:
        """ Connect all Qt signals on GUI load. """
        signals = {self.w_input.textEdited:      "search_input",
                   self.w_matches.itemSelected:  "search_choose_match",
                   self.w_mappings.itemSelected: "search_choose_mapping",
                   self.w_strokes.toggled:       "search_mode_strokes",
                   self.w_regex.toggled:         "search_mode_regex"}
        for signal, cmd_key in signals.items():
            signal.connect(partial(self.engine_call, cmd_key))

    @on("gui_set_enabled")
    def set_enabled(self, enabled:bool) -> None:
        """ Enable/disable all search widgets. """
        self.w_input.clear()
        self.w_input.setPlaceholderText("Search..." if enabled else "")
        self.w_matches.clear()
        self.w_mappings.clear()
        self.w_input.setEnabled(enabled)
        self.w_matches.setEnabled(enabled)
        self.w_mappings.setEnabled(enabled)
        self.w_strokes.setEnabled(enabled)
        self.w_regex.setEnabled(enabled)

    set_input = on("new_search_input")(delegate_to("w_input.setText"))

    set_matches = on("new_search_match_list")(delegate_to("w_matches.set_items"))
    select_matches = on("new_search_match_selection")(delegate_to("w_matches.select"))

    set_mappings = on("new_search_mapping_list")(delegate_to("w_mappings.set_items"))
    select_mappings = on("new_search_mapping_selection")(delegate_to("w_mappings.select"))
