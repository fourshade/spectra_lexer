from PyQt5.QtWidgets import QMainWindow, QFileDialog

from spectra_lexer import SpectraComponent
from spectra_lexer.gui_qt.display import GUIQtDisplay
from spectra_lexer.gui_qt.menu import GUIQtMenu
from spectra_lexer.gui_qt.search import GUIQtSearch
from spectra_lexer.gui_qt.window_ui import Ui_BaseWindow


class BaseWindow(QMainWindow, Ui_BaseWindow, SpectraComponent):
    """
    Base class for QT application window as created from the command line script or Plover.
    Contains all GUI elements as attributes and delegates GUI callbacks to subcomponents.
    """

    def __init__(self):
        super().__init__()
        self.setupUi(self)
        # Menu subcomponent; only used in standalone mode (top).
        menu = GUIQtMenu(self.m_menu, self.m_file, self.m_file_load, self.m_file_exit)
        # Search subcomponent; initialized with all search-related GUI elements (left half).
        search = GUIQtSearch(self.w_search_input, self.w_search_matches, self.w_search_mappings,
                                  self.w_search_type, self.w_search_regex)
        # Display subcomponent; initialized with all output-related GUI elements (right half).
        display = GUIQtDisplay(self.w_display_title, self.w_display_text,
                                    self.w_display_desc, self.w_display_board)
        self.add_commands({"window_close":       self.close,
                           "window_dialog_load": self.dialog_load})
        self.add_children([menu, search, display])

    def dialog_load(self, *args) -> None:
        """ Present a dialog for the user to select a steno dictionary file.
            Attempt to load it if not empty. *args is necessary to eat extra args from Qt signal. """
        file_formats = self.engine_call("file_get_decodable_exts")
        (fname, _) = QFileDialog.getOpenFileName(self, 'Load Dictionary', '.',
                                                 "Supported file formats (*" + " *".join(file_formats) + ")")
        if fname:
            self.engine_call("file_load_translations", [fname], "file dialog")
