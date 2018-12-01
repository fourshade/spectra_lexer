import sys
from typing import Iterable, List

from PyQt5.QtWidgets import QFileDialog, QMainWindow

from spectra_lexer import SpectraApplication
from spectra_lexer.engine import SpectraEngineComponent
from spectra_lexer.gui_qt.main_window_ui import Ui_MainWindow


class MainWindow(QMainWindow, Ui_MainWindow, SpectraEngineComponent):
    """
    Main QT application window as called from the command line. Top-level class for standalone execution.

    Children:
    w_central - QWidget, top-most container for main window UI elements.
    w_main - MainWidget, handles all lexer tasks given a dictionary and/or steno translations from the user.
    m_menu - QMenuBar, main menu at the top of the window.
    """

    _app: SpectraApplication  # Top-level application object. Must be a singleton that retains state.

    def __init__(self, *args, **kwargs):
        """ Set up the application with the main GUI widget and the file menu interface (this object). """
        super().__init__(*args, **kwargs)
        self.setupUi(self)
        self._app = SpectraApplication(self.w_main, self)

    def engine_commands(self) -> dict:
        """ Individual components must define the signals they respond to and the appropriate callbacks. """
        return {"engine_start": self.on_engine_start,
                "new_window":   self.on_new_window,
                "gui_open_file_dialog": self.dialog_load,}

    def on_engine_start(self) -> None:
        """ Command-line arguments are assumed to be steno dictionary files. Load them on engine start. """
        if len(sys.argv) > 1:
            self._load_dicts(sys.argv[1:], "command line")
        else:
            # If no arguments were given, make an attempt to locate Plover's dictionaries and load those.
            self._load_dicts(None, "Plover config")

    def on_new_window(self) -> None:
        """ Connect the Qt signals to the engine once it's ready for GUI actions. """
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
