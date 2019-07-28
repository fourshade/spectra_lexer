from pkgutil import get_data

from PyQt5.QtWidgets import QMainWindow

from .main_window_ui import Ui_MainWindow
from ..icon import IconRenderer


class MainWindow(QMainWindow, Ui_MainWindow):
    """ Base class for Qt application window as created from the command line script or Plover. """

    def __init__(self):
        """ Set up the main window. """
        super().__init__()
        self.setupUi(self)
        icon_data = get_data(__package__, "icon.svg")
        icon = IconRenderer(icon_data).generate()
        self.setWindowIcon(icon)

    def widgets(self) -> dict:
        """ Map all Python widget classes to internal Qt Designer names. """
        return dict(window=self,
                    w_menu=self.m_menu,
                    w_board=self.w_display_board,
                    w_desc=self.w_display_desc,
                    w_title=self.w_display_title,
                    w_text=self.w_display_text,
                    w_input=self.w_search_input,
                    w_matches=self.w_search_matches,
                    w_mappings=self.w_search_mappings,
                    w_strokes=self.w_search_type,
                    w_regex=self.w_search_regex)

    def show(self) -> None:
        super().show()
        self.activateWindow()
        self.raise_()
