from typing import Optional

from PyQt5.QtWidgets import QFileDialog, QMainWindow, QWidget

from spectra_lexer import on, pipe, SpectraComponent


class GUIQtWindow(SpectraComponent):
    """ GUI engine component; handles top-level window operations separate from the Qt window object. """

    window: QMainWindow  # Main window object. Must be the parent of any new dialogs.

    def __init__(self, window:QWidget):
        super().__init__()
        self.window = window

    @on("configure")
    def show(self, show_menu=True, **cfg_dict) -> None:
        """ Show the window once the engine is fully initialized and sends the start signal.
            If the menu is used, add the basic window-based commands before displaying the window. """
        if show_menu:
            self.engine_call("gui_menu_add", "File", "Load Dictionary...", "sig_window_dialog_load")
            self.engine_call("gui_menu_add", "File", "Exit", "sig_window_close")
        self.window.show()

    @pipe("sig_window_dialog_load", "file_dict_load")
    def dialog_load(self) -> Optional[list]:
        """ Present a dialog for the user to select a dictionary file. Attempt to load it if not empty. """
        file_formats = self.engine_call("file_get_decodable_exts")
        (fname, _) = QFileDialog.getOpenFileName(self.window, 'Load Dictionary', '.',
                                                 "Supported file formats (*" + " *".join(file_formats) + ")")
        if not fname:
            return None
        self.engine_call("new_status", "Loaded dictionaries from file dialog.")
        return [fname]

    @on("sig_window_close")
    def close(self):
        """ Closing the window means hiding it if there are persistent references and destroying it otherwise. """
        self.window.close()
