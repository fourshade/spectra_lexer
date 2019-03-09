from functools import partialmethod

from PyQt5.QtWidgets import QFileDialog, QMainWindow

from spectra_lexer import Component


class GUIQtFileDialog(Component):
    """ Controls user-based file loading and window closing. This should be disabled in plugin mode. """

    load_rules = Option("menu", "File:Load Rules...", "rules_dialog")
    load_translations = Option("menu", "File:Load Translations...", "translations_dialog")
    sep = Option("menu", "File:SEPARATOR")
    close_window = Option("menu", "File:Exit", "gui_window_close")

    window: QMainWindow = None  # Main GUI window.

    @on("new_gui_window")
    def new_gui(self, window:QMainWindow) -> None:
        """ Save the required widget. """
        self.window = window

    def new_dialog(self, d_type:str) -> None:
        """ Present a dialog for the user to select files. Attempt to load them if not empty. """
        fmts = self.engine_call("file_get_extensions")
        title_msg = f"Load {d_type.title()}"
        filter_msg = f"Supported file formats (*{' *'.join(fmts)})"
        (filenames, _) = QFileDialog.getOpenFileNames(self.window, title_msg, ".", filter_msg)
        if filenames:
            self.engine_call("new_status", f"Loading {d_type}...")
            self.engine_call(d_type + "_load", filenames)
            self.engine_call("new_status", f"Loaded {d_type} from file dialog.")

    rules = on("rules_dialog")(partialmethod(new_dialog, "rules"))
    translations = on("translations_dialog")(partialmethod(new_dialog, "translations"))
