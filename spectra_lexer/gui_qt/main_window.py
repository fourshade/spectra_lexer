import sys

from PyQt5.QtWidgets import QFileDialog, QMainWindow

from spectra_lexer.file import get_file_formats, RawStenoDictionary
from spectra_lexer.gui_qt.main_window_ui import Ui_MainWindow


class MainWindow(QMainWindow, Ui_MainWindow):
    """
    Main QT application window as called from the command line.

    Children:
    w_central - QWidget, top-most container for main window UI elements.
    w_main - MainWidget, handles all lexer tasks given a dictionary and/or steno translations from the user.
    m_menu - QMenuBar, main menu at the top of the window.
    """

    def __init__(self, *args, **kwargs):
        """ Set up the window, which contains references to methods called by menu bar actions. """
        super().__init__(*args, **kwargs)
        self.setupUi(self)
        self.m_file_load.triggered.connect(self.dialog_load)
        self.m_file_exit.triggered.connect(sys.exit)
        # All command-line arguments are assumed to be steno dictionary files. Load them on start-up.
        if len(sys.argv) > 1:
            self.load_dicts(*sys.argv[1:])

    def dialog_load(self) -> None:
        """ Present a dialog for the user to select a steno dictionary file. Attempt to load it if not empty. """
        (fname, _) = QFileDialog.getOpenFileName(self, 'Load Steno Dictionary', '.',
                                                 "Supported file formats (*" + " *".join(get_file_formats()) + ")")
        if fname:
            self.load_dicts(fname)

    def load_dicts(self, *filenames:str) -> None:
        """ Attempt to load one or more steno dictionaries given by filename.
            If there is more than one, they will be merged. Give the results to the main widget. """
        d = RawStenoDictionary(*filenames)
        if d:
            self.w_main.set_dictionary(d)
