from spectra_lexer.gui import SearchPanel
from spectra_lexer.types import delegate_to


class GUIQtSearchPanel(SearchPanel):
    """ GUI Qt operations class for the left-hand search panel. """

    w_input = resource("gui:w_search_input")        # Input box for the user to enter a search string.
    w_matches = resource("gui:w_search_matches")    # List box to show the matches for the user's search.
    w_mappings = resource("gui:w_search_mappings")  # List box to show the mappings of a match selection.
    w_strokes = resource("gui:w_search_type")       # Check box: False = word search, True = stroke search.
    w_regex = resource("gui:w_search_regex")        # Check box: False = prefix search, True = regex search.

    @on("gui_load")
    def load(self) -> None:
        """ Connect all Qt signals on GUI load. """
        connectors = [self.w_input.textEdited.connect,
                      self.w_matches.itemSelected.connect,
                      self.w_mappings.itemSelected.connect,
                      self.w_strokes.toggled.connect,
                      self.w_regex.toggled.connect]
        self.connect_all(connectors)

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

    set_input = delegate_to("w_input.setText")
    set_matches = delegate_to("w_matches.set_items")
    select_matches = delegate_to("w_matches.select")
    set_mappings = delegate_to("w_mappings.set_items")
    select_mappings = delegate_to("w_mappings.select")
