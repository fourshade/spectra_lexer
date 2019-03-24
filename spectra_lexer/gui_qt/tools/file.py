from typing import Sequence

from PyQt5.QtWidgets import QFileDialog

from spectra_lexer import Component
from spectra_lexer.file import JSON


def FileDialog(parent:QFileDialog, title:str, fmts_msg:str, fmts:Sequence[str]) -> Sequence[str]:
    """ Create a modal file open dialog and return multiple file selections in a list.
        If the dialog is cancelled, return an empty list. """
    filter_msg = f"{fmts_msg} (*{' *'.join(fmts)})"
    return QFileDialog.getOpenFileNames(parent, title, ".", filter_msg)[0]


class FileDialogTool(Component):
    """ Controls user-based file loading and window closing. """

    load_rules = Resource("menu",   "File:Load Rules...",        ["file_dialog_open", "rules"])
    load_trans = Resource("menu",   "File:Load Translations...", ["file_dialog_open", "translations"])
    load_index = Resource("menu",   "File:Load Index...",        ["file_dialog_open", "index"])
    sep = Resource("menu",          "File:")
    close_window = Resource("menu", "File:Close",                ["gui_window_close"])

    window = Resource("gui", "window", None, "Main window object. Must be the parent of any new dialogs.")

    @on("file_dialog_open")
    def open_dialog(self, res_type:str) -> None:
        """ Present a dialog for the user to select files of a specific resource type. """
        title_msg = f"Load {res_type.title()}"
        # Currently only JSON-type files are supported for loading.
        fmts_msg = "JSON files"
        fmts = JSON.extensions()
        filenames = FileDialog(self.window, title_msg, fmts_msg, fmts)
        # Attempt to load the selected files (if any).
        if filenames:
            self.engine_call(f"{res_type}_load", filenames)
            self.engine_call("new_status", f"Loaded {res_type} from file dialog.")
