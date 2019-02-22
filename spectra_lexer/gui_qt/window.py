from typing import Iterable

from PyQt5.QtWidgets import QFileDialog, QMainWindow

from spectra_lexer import Component, on, pipe


class GUIQtWindow(Component):
    """ GUI engine component; handles top-level window operations separate from the Qt window object. """

    ROLE = "gui_window"

    window: QMainWindow  # Main window object. Must be the parent of any new dialogs.

    def __init__(self, window:QMainWindow):
        super().__init__()
        self.window = window

    @on("start")
    def start(self, show_file_menu:bool=True, **opts) -> None:
        """ Show the window once the engine is fully initialized and sends the start signal.
            If the file menu is used, add the basic window-based dialog commands first. """
        if show_file_menu:
            self.engine_call("gui_menu_add", "File", "Load Rules...", "file_dialog", "rules")
            self.engine_call("gui_menu_add", "File", "Load Translations...", "file_dialog", "translations")
            self.engine_call("gui_menu_add", "File", "Exit", "gui_window_close", sep_first=True)
        self.window.show()

    @pipe("new_file_dialog", "new_status")
    def _dialog_load(self, d_type:str, file_formats:Iterable[str]) -> str:
        """ Present a dialog for the user to select dictionary files. Attempt to load them if not empty. """
        (filenames, _) = QFileDialog.getOpenFileNames(self.window, 'Load {} Dictionaries'.format(d_type.title()), '.',
                                                      "Supported file formats (*" + " *".join(file_formats) + ")")
        if filenames:
            self.engine_call(d_type + "_load", filenames)
            return "Loaded {} from file dialog.".format(d_type)

    @on("gui_window_close")
    def close(self):
        """ Closing the window means hiding it if there are persistent references and destroying it otherwise. """
        self.window.close()
