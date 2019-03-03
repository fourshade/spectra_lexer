from typing import Dict, Iterable

from PyQt5.QtWidgets import QFileDialog, QMainWindow, QWidget

from spectra_lexer import Component, on


class GUIQtFileDialog(Component):
    """ GUI component to create file dialog windows and handle I/O from them. Also closes the main window. """

    ROLE = "gui_file"

    window: QMainWindow  # Main window object. Must be the parent of any new dialogs.

    @on("new_gui_window")
    def start(self, widgets:Dict[str, QWidget]) -> None:
        """ If the file menu is used, add the basic file dialog commands and the exit command. """
        self.window = widgets["window"][0]
        self.engine_call("gui_menu_add", "File", "Load Rules...", "file_dialog", "rules")
        self.engine_call("gui_menu_add", "File", "Load Translations...", "file_dialog", "translations")
        self.engine_call("gui_menu_add", "File", "Exit", "gui_window_close", sep_first=True)

    @on("new_file_dialog")
    def new_dialog(self, d_type:str, file_formats:Iterable[str]) -> None:
        """ Present a dialog for the user to select dictionary files. Attempt to load them if not empty. """
        title_msg = f"Load {d_type.title()} Dictionaries"
        filter_msg = f"Supported file formats (*{' *'.join(file_formats)})"
        (filenames, _) = QFileDialog.getOpenFileNames(self.window, title_msg, ".", filter_msg)
        if filenames:
            self.engine_call("new_status", f"Loading {d_type}...")
            self.engine_call(d_type + "_load", filenames)
            self.engine_call("new_status", f"Loaded {d_type} from file dialog.")
