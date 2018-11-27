import sys
from functools import partial
from typing import Iterable, Dict, List

from PyQt5.QtWidgets import QFileDialog, QMainWindow

from spectra_lexer.engine import SpectraEngine, SpectraEngineComponent
from spectra_lexer.gui_qt.main_window_ui import Ui_MainWindow
from spectra_lexer.file import FileHandler
from spectra_lexer.display.cascaded_text import CascadedTextDisplay
from spectra_lexer.lexer import StenoLexer
from spectra_lexer.search import SearchEngine

class MainWindow(QMainWindow, Ui_MainWindow, SpectraEngineComponent):
    """
    Main QT application window as called from the command line. Top-level class for standalone execution.

    Children:
    w_central - QWidget, top-most container for main window UI elements.
    w_main - MainWidget, handles all lexer tasks given a dictionary and/or steno translations from the user.
    m_menu - QMenuBar, main menu at the top of the window.
    """

    def __init__(self, *args, **kwargs):
        """ Set up the window, which contains references to methods called by menu bar actions. """
        super().__init__(*args, **kwargs)
        self.setupUi(self)
        # Make the engine, add everything to it, and start it.
        SpectraEngine(FileHandler(), StenoLexer(), SearchEngine(),
                      CascadedTextDisplay(), self.w_main, self).start()
        # All command-line arguments are assumed to be steno dictionary files. Load them on start-up.
        # If none were given, make an attempt to locate Plover's dictionaries and load those.
        if len(sys.argv) > 1:
            self._load_dicts(sys.argv[1:], "command line")
        else:
            self._load_dicts(None, "Plover config")
        # Send command to set up anything else that needs it for a new GUI.
        self.engine_send("new_window")

    def engine_commands(self) -> dict:
        """ Individual components must define the signals they respond to and the appropriate callbacks. """
        return {"gui_open_file_dialog": self.dialog_load}

    def engine_connect(self, engine:SpectraEngine) -> None:
        """ At engine connect, route all Qt signals to their corresponding engine signals (or other methods). """
        super().engine_connect(engine)
        self.m_file_load.triggered.connect(lambda *args: self.engine_send("file_get_dict_formats"))
        self.m_file_exit.triggered.connect(sys.exit)

    def dialog_load(self, file_formats:List[str]) -> None:
        """ Present a dialog for the user to select a steno dictionary file. Attempt to load it if not empty. """
        (fname, _) = QFileDialog.getOpenFileName(self, 'Load Steno Dictionary', '.',
                                                 "Supported file formats (*" + " *".join(file_formats) + ")")
        if fname:
            self._load_dicts((fname,), "file dialog")

    def _load_dicts(self, filenames:Iterable[str]=None, src_string:str="") -> None:
        self.engine_send("file_load_steno_dicts", filenames)
        if src_string:
            self.engine_send("gui_show_status_message", "Loaded dictionaries from {}.".format(src_string))
