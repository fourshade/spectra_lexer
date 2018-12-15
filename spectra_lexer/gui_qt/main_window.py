import sys

from PyQt5.QtWidgets import QFileDialog, QMainWindow

from spectra_lexer.gui_qt import GUIQtComponent
from spectra_lexer.gui_qt.display import GUIQtDisplay
from spectra_lexer.gui_qt.main_window_ui import Ui_MainWindow
from spectra_lexer.gui_qt.search import GUIQtSearch


class MainWindow(QMainWindow, Ui_MainWindow, GUIQtComponent):
    """
    Main QT application window as created from the command line script or Plover.
    Contains all GUI elements as attributes and delegates most GUI callbacks to subcomponents.
    """

    _search: GUIQtSearch    # Search subcomponent; initialized with all search-related GUI elements (left half)
    _display: GUIQtDisplay  # Display subcomponent; initialized with all output-related GUI elements (right half)

    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self._search = GUIQtSearch(self.w_search_input, self.w_search_matches, self.w_search_mappings,
                                   self.w_search_type,  self.w_search_regex)
        self._display = GUIQtDisplay(self.w_display_title, self.w_display_text,
                                     self.w_display_desc,  self.w_display_board)

    def engine_commands(self) -> dict:
        """ Individual components must define the signals they respond to and the appropriate callbacks.
            Some commands have identical signatures to the Qt GUI methods; those can be passed directly. """
        return {**super().engine_commands(),
                "set_status_message": self.w_display_title.setText}

    def engine_subcomponents(self) -> tuple:
        """ Components provide a tuple of subcomponents to connect here. """
        return (*super().engine_subcomponents(), self._search, self._display)

    def on_new_window(self) -> None:
        """ Route all Qt signals to their corresponding engine signals (or other methods) once the engine is ready. """
        super().on_new_window()
        # Menu signals provide arguments that the callees don't expect, so discard them in a lambda first.
        self.m_file_load.triggered.connect(lambda *args: self.dialog_load())
        self.m_file_exit.triggered.connect(lambda *args: sys.exit())

    def dialog_load(self) -> None:
        """ Present a dialog for the user to select a steno dictionary file. Attempt to load it if not empty. """
        file_formats = self.engine_call("file_get_dict_formats")
        (fname, _) = QFileDialog.getOpenFileName(self, 'Load Steno Dictionary', '.',
                                                 "Supported file formats (*" + " *".join(file_formats) + ")")
        if fname:
            self.engine_call("dialog_translations_chosen", (fname,))
