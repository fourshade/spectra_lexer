from typing import Dict, List

from PyQt5.QtWidgets import QMainWindow, QWidget

from spectra_lexer.gui_qt.main_window_ui import Ui_MainWindow


class MainWindow(QMainWindow, Ui_MainWindow):
    """ Base class for QT application window as created from the command line script or Plover. """

    def __init__(self):
        super().__init__()
        self.setupUi(self)

    def partition(self) -> Dict[str, List[QWidget]]:
        """ Partition all GUI elements into sections for the engine. """
        return {
            # Top-level window.
            "window": [self],
            # Menu bar; only used in standalone mode (top).
            "menu":   [self.m_menu],
            # Search-related GUI elements (left half).
            "search": [self.w_search_input, self.w_search_matches, self.w_search_mappings,
                       self.w_search_type, self.w_search_regex],
            # Text output GUI elements (top-right half).
            "text":   [self.w_display_title, self.w_display_text],
            # Board diagram GUI elements (bottom-right half).
            "board":  [self.w_display_desc, self.w_display_board]
        }
