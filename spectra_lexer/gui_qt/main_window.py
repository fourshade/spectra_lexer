import sys
from typing import Iterable

from PyQt5.QtWidgets import QFileDialog, QMainWindow

from spectra_lexer.gui_qt import GUIQtComponent
from spectra_lexer.gui_qt.display import GUIQtDisplay
from spectra_lexer.gui_qt.main_window_ui import Ui_MainWindow
from spectra_lexer.gui_qt.search import GUIQtSearch


class MainWindow(QMainWindow, Ui_MainWindow, GUIQtComponent):
    """
    Main QT application window as created from the command line script or Plover.
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

    def __init__(self):
        super().__init__()
        self.setupUi(self)

    def engine_commands(self) -> dict:
        """ Individual components must define the signals they respond to and the appropriate callbacks.
            Some commands have identical signatures to the Qt GUI methods; those can be passed directly. """
        return {**super().engine_commands(),
                "gui_open_file_dialog": self.dialog_load,
                "set_status_message":   self.w_display_title.setText}

    def engine_subcomponents(self) -> tuple:
        """ Components provide a tuple of subcomponents to connect here.  """
        return (*super().engine_subcomponents(),
                GUIQtSearch(self.w_search_input,
                            self.w_search_matches,
                            self.w_search_mappings,
                            self.w_search_type,
                            self.w_search_regex, ),
                GUIQtDisplay(self.w_display_title,
                             self.w_display_text,
                             self.w_display_desc,
                             self.w_display_board))

    def on_new_window(self) -> None:
        """ Route all Qt signals to their corresponding engine signals (or other methods) once the engine is ready. """
        super().on_new_window()
        # Menu signals provide arguments that the callees don't expect, so discard them in a lambda first.
        self.m_file_load.triggered.connect(lambda *args: self.engine_send("file_get_dict_formats"))
        self.m_file_exit.triggered.connect(lambda *args: sys.exit())

    def dialog_load(self, file_formats:Iterable[str]) -> None:
        """ Present a dialog for the user to select a steno dictionary file. Attempt to load it if not empty. """
        (fname, _) = QFileDialog.getOpenFileName(self, 'Load Steno Dictionary', '.',
                                                 "Supported file formats (*" + " *".join(file_formats) + ")")
        if fname:
            self.engine_send("file_load_steno_dicts", (fname,))
            self.engine_send("set_status_message", "Loaded new dictionaries from file dialog.")
