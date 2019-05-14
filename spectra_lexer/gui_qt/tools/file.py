from functools import partial
from typing import Iterable

from PyQt5.QtWidgets import QFileDialog

from .menu import MenuCommand
from ..window import GUI
from spectra_lexer.core import Component
from spectra_lexer.steno import LXIndex, LXTranslations
from spectra_lexer.system import SYSControl


class GUIQTFile:

    _FileCommand = partial(MenuCommand, "File")

    @_FileCommand("Load Translations...")
    def open_translations(self) -> None:
        raise NotImplementedError

    @_FileCommand("Load Index...")
    def open_index(self) -> None:
        raise NotImplementedError

    m_sep = _FileCommand()()

    @_FileCommand("Close")
    def exit(self) -> None:
        raise NotImplementedError


class QtFileTool(Component, GUIQTFile,
                 GUI.Window):
    """ Controls user-based file loading and program exit. """

    def open_translations(self) -> None:
        self.open(LXTranslations, "translations", ".json")

    def open_index(self) -> None:
        self.open(LXIndex, "index", ".json")

    def exit(self) -> None:
        self.engine_call(SYSControl.exit)

    def open(self, load_interface, res_type:str, file_ext:str) -> None:
        """ Present a dialog for the user to select files of a specific resource type. """
        filename = self._load_dialog(f"Load {res_type.title()}", [file_ext])
        # Attempt to load the selected file (if any).
        if filename:
            self.engine_call(load_interface.load, filename)
            self.engine_call(SYSControl.status, f"Loaded {res_type} from file dialog.")

    def _load_dialog(self, title:str, fmts:Iterable[str]) -> str:
        """ Present a modal dialog with <title> to select any one file with an extension in <fmts> for loading.
            Send a file selection to the callback. If the dialog is cancelled, send an empty list. """
        filter_msg = f"Supported files (*{' *'.join(fmts)})"
        return QFileDialog.getOpenFileName(self.window, title, ".", filter_msg)[0]
