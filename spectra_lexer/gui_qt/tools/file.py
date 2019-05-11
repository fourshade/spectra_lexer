from typing import Iterable

from PyQt5.QtWidgets import QFileDialog

from .base import GUIQtTool
from spectra_lexer.gui import FileTool


class GUIQtFileTool(GUIQtTool, FileTool):
    """ Controls user-based file loading and window closing. """

    def get_filename_load(self, title:str, fmts:Iterable[str]) -> str:
        """ Create a modal file open dialog and send a file selection to the callback.
            If the dialog is cancelled, send an empty list. """
        filter_msg = f"Supported files (*{' *'.join(fmts)})"
        return QFileDialog.getOpenFileName(self.window, title, ".", filter_msg)[0]
