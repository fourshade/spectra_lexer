from typing import Iterable

from PyQt5.QtWidgets import QFileDialog

from spectra_lexer.gui import FileTool


class GUIQtFileTool(FileTool):
    """ Controls user-based file loading and window closing. """

    window = resource("gui:window", desc="Main window object. Must be the parent of any new dialogs.")

    def get_filename(self, title:str, fmts_msg:str, fmts:Iterable[str]) -> str:
        """ Create a modal file open dialog and send a file selection to the callback.
            If the dialog is cancelled, send an empty list. """
        filter_msg = f"{fmts_msg} (*{' *'.join(fmts)})"
        return QFileDialog.getOpenFileName(self.window, title, ".", filter_msg)[0]
