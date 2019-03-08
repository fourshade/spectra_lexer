from typing import Dict, List

from PyQt5.QtWidgets import QMainWindow, QWidget

from .main_window_ui import Ui_MainWindow


class MainWindow(QMainWindow, Ui_MainWindow):
    """ Base class for Qt application window as created from the command line script or Plover. """

    def __init__(self):
        """ Set up the main window. """
        super().__init__()
        self.setupUi(self)

    @property
    def widgets(self) -> Dict[str, List[QWidget]]:
        """ Return a dict partitioning all widgets using dynamic Python code into sections. """
        return {"window": [self],                                       # Top-level window (this object)
                "menu":   [self.m_menu],                                # Menu bar (top)
                "search": [self.w_search_input, self.w_search_matches,  # Search-related GUI elements (left half)
                           self.w_search_mappings, self.w_search_type, self.w_search_regex],
                "text":   [self.w_display_title, self.w_display_text],  # Text output GUI elements (top-right half)
                "board":  [self.w_display_desc, self.w_display_board]}  # Board diagram GUI elements (bottom-right half)
