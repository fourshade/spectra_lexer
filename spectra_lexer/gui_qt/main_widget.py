from functools import partial

from PyQt5.QtWidgets import QWidget

from spectra_lexer.engine import SpectraEngineComponent, SpectraEngine
from spectra_lexer.gui_qt.main_widget_ui import Ui_MainWidget


class MainWidget(QWidget, Ui_MainWidget, SpectraEngineComponent):
    """
    Main widget container for all GUI elements and the initial recipient of all GUI callbacks.

    Interactive children:
        Input:
            w_search_input    - QLineEdit, input box for the user to enter a search string.
            w_search_matches  - QListView, list box to show the direct matches for the user's search.
            w_search_mappings - QListView, list box to show the mappings of a selection in the match list.
            w_search_type     - QCheckBox, determines whether to use word or stroke search.
            w_search_regex    - QCheckBox, determines whether to use prefix or regex search.
        Output:
            w_display_title - QLineEdit, displays status messages and mapping of keys to word.
            w_display_text  - QTextEdit, displays formatted text breakdown graph.
            w_display_desc  - QLineEdit, displays rule description.
            w_display_board - QWidget, displays steno board diagram.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setupUi(self)

    def engine_commands(self) -> dict:
        """ Individual components must define the signals they respond to and the appropriate callbacks.
            Some commands have identical signatures to the Qt GUI methods; those can be passed directly. """
        return {"gui_reset_search":        self.reset_search,
                "gui_set_match_list":      self.w_search_matches.set_items,
                "gui_set_mapping_list":    self.w_search_mappings.set_items,
                "gui_select_match":        self.w_search_matches.select,
                "gui_select_mapping":      self.w_search_mappings.select,
                "gui_show_status_message": self.w_display_title.setText,
                "gui_display_title":       self.w_display_title.setText,
                "gui_display_graph":       self.w_display_text.set_graph,
                "gui_display_info":        self.display_info,}

    def engine_connect(self, engine:SpectraEngine) -> None:
        """ At engine connect, route all Qt signals to their corresponding engine signals (or other methods). """
        super().engine_connect(engine)
        SLOT_ROUTING_TABLE = {self.w_search_input.textEdited:         "search_query",
                              self.w_search_matches.itemSelected:     "search_choose_match",
                              self.w_search_mappings.itemSelected:    "search_choose_mapping",
                              self.w_search_type.toggled:             "search_set_stroke_search",
                              self.w_search_regex.toggled:            "search_set_regex_enabled",
                              self.w_display_text.mouseOverCharacter: "display_info_at"}
        for (slot, cmd) in SLOT_ROUTING_TABLE.items():
            slot.connect(partial(self.engine_send, cmd))

    # Search widgets
    def reset_search(self, enabled:bool) -> None:
        """ Reset all search elements, then enable/disable them according to the argument. """
        self.w_search_input.setPlaceholderText("Search...")
        self.w_search_type.setChecked(False)
        self.w_search_regex.setChecked(False)
        for w in (self.w_search_input, self.w_search_matches, self.w_search_mappings):
            w.clear()
            w.setEnabled(enabled)

    # Display widgets
    def display_info(self, keys:str, desc:str) -> None:
        """ Send the given rule info to the board info widgets. """
        self.w_display_desc.setText(desc)
        self.w_display_board.show_keys(keys)
