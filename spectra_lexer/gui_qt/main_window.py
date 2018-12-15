from functools import partial
import sys
from typing import List

from PyQt5.QtWidgets import QFileDialog, QMainWindow

from spectra_lexer import SpectraApplication
from spectra_lexer.engine import SpectraEngineComponent
from spectra_lexer.gui_qt.main_window_ui import Ui_MainWindow


class MainWindow(QMainWindow, Ui_MainWindow, SpectraEngineComponent):
    """
    Main QT application window as called from the command line or Plover.
    Contains all GUI elements and is the initial recipient of all GUI callbacks.

    Interactive children:
        m_menu            - QMenuBar, main menu at the top of the window. Hidden when used as Plover plugin.
        w_search_input    - QLineEdit, input box for the user to enter a search string.
        w_search_matches  - QListView, list box to show the direct matches for the user's search.
        w_search_mappings - QListView, list box to show the mappings of a selection in the match list.
        w_search_type     - QCheckBox, determines whether to use word or stroke search.
        w_search_regex    - QCheckBox, determines whether to use prefix or regex search.
        w_display_title   - QLineEdit, displays status messages and mapping of keys to word.
        w_display_text    - QTextEdit, displays formatted text breakdown graph.
        w_display_desc    - QLineEdit, displays rule description.
        w_display_board   - QWidget, displays steno board diagram.
    """

    _app: SpectraApplication  # Top-level application object. Must be a singleton that retains state.

    def __init__(self, *args, **kwargs):
        """ Set up the application with the main GUI widget/file menu interface (this object).
            If Plover was responsible for initialization, its components will be in args, so add them too. """
        super().__init__()
        self.setupUi(self)
        self._app = SpectraApplication(self, *args, **kwargs)

    def engine_commands(self) -> dict:
        """ Individual components must define the signals they respond to and the appropriate callbacks.
            Some commands have identical signatures to the Qt GUI methods; those can be passed directly. """
        return {"new_window":              self.on_new_window,
                "gui_open_file_dialog":    self.dialog_load,
                "gui_reset_search":        self.reset_search,
                "gui_set_match_list":      self.w_search_matches.set_items,
                "gui_set_mapping_list":    self.w_search_mappings.set_items,
                "gui_select_match":        self.w_search_matches.select,
                "gui_select_mapping":      self.w_search_mappings.select,
                "gui_show_status_message": self.w_display_title.setText,
                "gui_display_title":       self.w_display_title.setText,
                "gui_display_graph":       self.w_display_text.set_graph,
                "gui_display_info":        self.display_info,}

    def on_new_window(self) -> None:
        """ Route all Qt signals to their corresponding engine signals (or other methods) once the engine is ready. """
        SLOT_ROUTING_TABLE = {self.w_search_input.textEdited:         "search_query",
                              self.w_search_matches.itemSelected:     "search_choose_match",
                              self.w_search_mappings.itemSelected:    "search_choose_mapping",
                              self.w_search_type.toggled:             "search_set_stroke_search",
                              self.w_search_regex.toggled:            "search_set_regex_enabled",
                              self.w_display_text.mouseOverCharacter: "display_info_at"}
        for (slot, cmd) in SLOT_ROUTING_TABLE.items():
            slot.connect(partial(self.engine_send, cmd))
        # Menu signals provide arguments that the callees don't expect, so discard them in a lambda first.
        self.m_file_load.triggered.connect(lambda *args: self.engine_send("file_get_dict_formats"))
        self.m_file_exit.triggered.connect(lambda *args: sys.exit())

    # Menu widget
    def dialog_load(self, file_formats:List[str]) -> None:
        """ Present a dialog for the user to select a steno dictionary file. Attempt to load it if not empty. """
        (fname, _) = QFileDialog.getOpenFileName(self, 'Load Steno Dictionary', '.',
                                                 "Supported file formats (*" + " *".join(file_formats) + ")")
        if fname:
            self.engine_send("file_load_steno_dicts", (fname,))
            self.w_display_title.setText("Loaded new dictionaries from file dialog.")

    # Search widgets
    def reset_search(self, enabled:bool) -> None:
        """ Reset all search widgets, then enable/disable them according to the argument. """
        self.w_search_input.clear()
        self.w_search_input.setPlaceholderText("Search..." if enabled else "No dictionaries.")
        self.w_search_matches.clear()
        self.w_search_mappings.clear()
        self.w_search_type.setChecked(False)
        self.w_search_regex.setChecked(False)
        for w in (self.w_search_input, self.w_search_matches, self.w_search_mappings,
                  self.w_search_type, self.w_search_regex):
            w.setEnabled(enabled)

    # Display widgets
    def display_info(self, keys:str, desc:str) -> None:
        """ Send the given rule info to the board info widgets. """
        self.w_display_desc.setText(desc)
        self.w_display_board.show_keys(keys)
