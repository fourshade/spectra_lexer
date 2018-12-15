from PyQt5.QtWidgets import QMainWindow, QFileDialog

from spectra_lexer.gui_qt import GUIQtComponent
from spectra_lexer.gui_qt.display import GUIQtDisplay
from spectra_lexer.gui_qt.menu import GUIQtMenu
from spectra_lexer.gui_qt.search import GUIQtSearch
from spectra_lexer.gui_qt.window_ui import Ui_BaseWindow


class BaseWindow(QMainWindow, Ui_BaseWindow, GUIQtComponent):
    """
    Abstract base class for QT application window as created from the command line script or Plover.
    Contains all GUI elements as attributes and delegates GUI callbacks to subcomponents.
    """

    menu: GUIQtMenu        # Menu subcomponent; only used in standalone mode (top).
    search: GUIQtSearch    # Search subcomponent; initialized with all search-related GUI elements (left half).
    display: GUIQtDisplay  # Display subcomponent; initialized with all output-related GUI elements (right half).

    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.menu = GUIQtMenu(self.m_menu, self.m_file, self.m_file_load, self.m_file_exit)
        self.search = GUIQtSearch(self.w_search_input, self.w_search_matches, self.w_search_mappings,
                                  self.w_search_type, self.w_search_regex)
        self.display = GUIQtDisplay(self.w_display_title, self.w_display_text,
                                    self.w_display_desc, self.w_display_board)

    def engine_commands(self) -> dict:
        """ Individual components must define the signals they respond to and the appropriate callbacks.
            Some commands have identical signatures to the Qt GUI methods; those can be passed directly. """
        return {**super().engine_commands(),
                "gui_dialog_load_dict": self.dialog_load_dict,
                "log_exception":        self.w_display_text.setPlainText,
                "set_status_message":   self.w_display_title.setText}

    def engine_subcomponents(self) -> tuple:
        """ Components provide a tuple of subcomponents to connect here. """
        return (*super().engine_subcomponents(), self.menu, self.search, self.display)

    def dialog_load_dict(self, file_formats) -> None:
        """ Present a dialog for the user to select a dictionary file and return it. """
        (fname, _) = QFileDialog.getOpenFileName(self, 'Load Dictionary', '.',
                                                 "Supported file formats (*" + " *".join(file_formats) + ")")
        return fname


class MainWindow(BaseWindow):
    """ Main QT application window for standalone operation as created from the command line script. """
