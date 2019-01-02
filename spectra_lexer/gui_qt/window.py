from typing import Optional, List

from PyQt5.QtWidgets import QMainWindow, QFileDialog, QWidget

from spectra_lexer import on, pipe, SpectraComponent
from spectra_lexer.gui_qt.board import GUIQtBoardDisplay
from spectra_lexer.gui_qt.menu import GUIQtMenu
from spectra_lexer.gui_qt.search import GUIQtSearch
from spectra_lexer.gui_qt.text import GUIQtTextDisplay
from spectra_lexer.gui_qt.window_ui import Ui_BaseWindow


class MainWindow(QMainWindow, Ui_BaseWindow):
    """ Base class for QT application window as created from the command line script or Plover. """

    def __init__(self):
        super().__init__()
        self.setupUi(self)

    def partition(self) -> List[SpectraComponent]:
        """ Partition all GUI elements into engine components. """
        # Top-level window handler.
        window = GUIQtWindow(self)
        # Menu component; only used in standalone mode (top).
        menu = GUIQtMenu(self.m_menu)
        # Search component; initialized with all search-related GUI elements (left half).
        search = GUIQtSearch(self.w_search_input, self.w_search_matches, self.w_search_mappings,
                             self.w_search_type, self.w_search_regex)
        # Text display component; initialized with text output GUI elements (top-right half).
        text = GUIQtTextDisplay(self.w_display_title, self.w_display_text)
        # Board display component; initialized with board diagram GUI elements (bottom-right half).
        board = GUIQtBoardDisplay(self.w_display_desc, self.w_display_board)
        return [window, menu, search, text, board]


class GUIQtWindow(SpectraComponent):
    """ Top-level GUI engine component, which holds QMainWindow (inheritance from both is too convoluted).
        Handles top-level window operations separate from the Qt window object. """

    window: QMainWindow  # Main window object. Must be the parent of any new dialogs.

    def __init__(self, window:QWidget):
        super().__init__()
        self.window = window

    @on("configure")
    def show(self, *args, **kwargs) -> None:
        """ Show the window once the engine is fully initialized and sends the start signal.
            Menu commands are handled here, so add the basic ones before displaying the window. """
        self.engine_send("menu_add", "File", "Load Dictionary...", "sig_window_dialog_load")
        self.engine_send("menu_add", "File", "Exit", "sig_window_close")
        self.window.show()

    @pipe("sig_window_dialog_load", "file_dict_load")
    def dialog_load(self) -> Optional[list]:
        """ Present a dialog for the user to select a dictionary file. Attempt to load it if not empty. """
        file_formats = self.engine_call("file_get_decodable_exts")
        (fname, _) = QFileDialog.getOpenFileName(self.window, 'Load Dictionary', '.',
                                                 "Supported file formats (*" + " *".join(file_formats) + ")")
        if not fname:
            return None
        self.engine_send("new_status", "Loaded dictionaries from file dialog.")
        return [fname]

    @on("sig_window_close")
    def close(self):
        """ Closing the window means hiding it if there are persistent references and destroying it otherwise. """
        self.window.close()
