from typing import Iterable

from PyQt5.QtWidgets import QFileDialog

from .base import GUIQT_TOOL


class QtFileTool(GUIQT_TOOL):
    """ Controls user-based file loading and program exit. """

    def file_open_translations(self) -> None:
        self._open("translations", ".json")

    def file_open_index(self) -> None:
        self._open("index", ".json")

    def file_exit(self) -> None:
        self.Exit()

    def _open(self, res_type:str, file_ext:str) -> None:
        """ Present a dialog for the user to select files of a specific resource type. """
        filename = self._load_dialog(f"Load {res_type.title()}", [file_ext])
        # Attempt to load the selected file (if any).
        if filename:
            getattr(self, f"RS{res_type.title()}Load")(filename)
            self.SYSStatus(f"Loaded {res_type} from file dialog.")

    def _load_dialog(self, title:str, fmts:Iterable[str]) -> str:
        """ Present a modal dialog with <title> to select any one file with an extension in <fmts> for loading.
            Send a file selection to the callback. If the dialog is cancelled, send an empty list. """
        filter_msg = f"Supported files (*{' *'.join(fmts)})"
        return QFileDialog.getOpenFileName(self.WINDOW, title, ".", filter_msg)[0]
