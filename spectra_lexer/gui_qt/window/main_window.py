from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QMainWindow

from .main_window_ui import Ui_MainWindow


class MainWindow(QMainWindow, Ui_MainWindow):
    """ Main GUI window with pre-defined Qt designer widgets. """

    def __init__(self) -> None:
        super().__init__()
        self.setupUi(self)

    def map_widgets(self) -> dict:
        """ Map all Python widget classes to internal Qt Designer names. """
        return dict(w_board=self.w_display_board,
                    w_desc=self.w_display_desc,
                    w_title=self.w_display_title,
                    w_text=self.w_display_text,
                    w_input=self.w_search_input,
                    w_matches=self.w_search_matches,
                    w_mappings=self.w_search_mappings,
                    w_strokes=self.w_search_type,
                    w_regex=self.w_search_regex)

    def load_icon(self, filename:str) -> None:
        """ Set up the main window icon from a filename. """
        icon = QIcon(filename)
        self.setWindowIcon(icon)

    def show(self) -> None:
        """ Show the window, move it in front of other windows, and activate focus. """
        super().show()
        self.activateWindow()
        self.raise_()
