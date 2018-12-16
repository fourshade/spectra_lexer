from typing import List

from PyQt5.QtWidgets import QMainWindow, QFileDialog

from spectra_lexer import on, SpectraComponent
from spectra_lexer.gui_qt.display import GUIQtDisplay
from spectra_lexer.gui_qt.menu import GUIQtMenu
from spectra_lexer.gui_qt.search import GUIQtSearch
from spectra_lexer.gui_qt.window_ui import Ui_BaseWindow


class MainWindow(QMainWindow, Ui_BaseWindow):
    """
    Base class for QT application window as created from the command line script or Plover.
    Contains all GUI elements as attributes and partitions these into engine components.
    """

    components: List[SpectraComponent]  # List of pre-built engine components for the application.

    def __init__(self):
        super().__init__()
        self.setupUi(self)
        # Window component; handles top-level window operations separate from this Qt window object.
        window = GUIQtWindow(self)
        # Menu component; only used in standalone mode (top).
        menu = GUIQtMenu(self.m_menu, self.m_file, self.m_file_load, self.m_file_exit)
        # Search component; initialized with all search-related GUI elements (left half).
        search = GUIQtSearch(self.w_search_input, self.w_search_matches, self.w_search_mappings,
                             self.w_search_type, self.w_search_regex)
        # Display component; initialized with all output-related GUI elements (right half).
        display = GUIQtDisplay(self.w_display_title, self.w_display_text,
                               self.w_display_desc, self.w_display_board)
        self.components = [window, menu, search, display]


class GUIQtWindow(SpectraComponent):
    """ Top-level GUI engine component, distinct from QMainWindow (inheritance from both is too convoluted).
        Handles general window operations only. """

    window: QMainWindow  # Main window object. Must be the parent of any new dialogs.

    def __init__(self, window:QMainWindow):
        super().__init__()
        self.window = window

    @on("new_window")
    def show(self) -> None:
        """ Only show the window once the engine is fully initialized and sends the signal. """
        self.window.show()

    @on("window_close")
    def close(self):
        """ Closing the window means hiding it if there are persistent references and destroying it otherwise. """
        self.window.close()

    @on("window_dialog_load")
    def dialog_load(self) -> None:
        """ Present a dialog for the user to select a steno dictionary file. Attempt to load it if not empty. """
        file_formats = self.engine_call("file_get_decodable_exts")
        (fname, _) = QFileDialog.getOpenFileName(self.window, 'Load Dictionary', '.',
                                                 "Supported file formats (*" + " *".join(file_formats) + ")")
        if fname:
            self.engine_call("file_load_translations", [fname], "file dialog")
