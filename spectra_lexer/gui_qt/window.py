from typing import Optional

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
    def start(self, show_menu=True, **opts) -> None:
        """ Show the window once the engine is fully initialized and sends the start signal.
            If the menu is used, add the basic window-based dialog commands before displaying the window. """
        if show_menu:
            self.engine_call("gui_menu_add", "File", "Load Rules...", "sig_menu_load_rules")
            self.engine_call("gui_menu_add", "File", "Load Translations...", "sig_menu_load_translations")
            self.engine_call("gui_menu_add", "File", "Exit", "sig_menu_window_close", sep_first=True)
        self.window.show()

    @pipe("sig_menu_load_rules", "dict_load_rules")
    def dialog_load_rules(self) -> Optional[list]:
        return self._dialog_load("rules")

    @pipe("sig_menu_load_translations", "dict_load_translations")
    def dialog_load_translations(self) -> Optional[list]:
        return self._dialog_load("translations")

    def _dialog_load(self, d_type:str) -> Optional[list]:
        """ Present a dialog for the user to select dictionary files. Attempt to load them if not empty. """
        file_formats = self.engine_call("file_get_supported_exts")
        (filenames, _) = QFileDialog.getOpenFileNames(self.window, 'Load {} Dictionaries'.format(d_type.title()), '.',
                                                      "Supported file formats (*" + " *".join(file_formats) + ")")
        if not filenames:
            return None
        self.engine_call("new_status", "Loaded {} from file dialog.".format(d_type))
        return filenames

    @on("sig_menu_window_close")
    def close(self):
        """ Closing the window means hiding it if there are persistent references and destroying it otherwise. """
        self.window.close()
