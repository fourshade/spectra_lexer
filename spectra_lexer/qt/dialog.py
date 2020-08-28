""" Wrapper functions for various Qt file selection dialogs. """

from typing import List, Optional, Type
from weakref import WeakValueDictionary

from PyQt5.QtWidgets import QFileDialog, QDialog, QMessageBox, QWidget


def _filter_str(file_exts="") -> str:
    """ Return a file dialog filter string based on file extensions (without the dot).
        If <file_exts> is empty, return a filter string matching any file.
        Multiple file extensions may be delimited by a | character. """
    if not file_exts:
        return "All files (*.*)"
    filters = [f"{ext.upper()} files (*.{ext})" for ext in file_exts.split("|")]
    return ";;".join(filters)


class DialogManager:
    """ Tracks standard dialogs and opens common modal dialogs and returns their results. """

    def __init__(self, parent:QWidget) -> None:
        self._parent = parent                         # All dialogs will be children of this widget.
        self._dialogs_by_cls = WeakValueDictionary()  # Contains the current instance of each dialog class.

    def load(self, dlg_cls:Type[QDialog]) -> Optional[QDialog]:
        """ If a previous <dlg_cls> is open, set focus on it and return None, otherwise return a new one. """
        dialog = self._dialogs_by_cls.get(dlg_cls)
        if dialog is not None and not dialog.isHidden():
            dialog.show()
            dialog.activateWindow()
            return None
        dialog = self._dialogs_by_cls[dlg_cls] = dlg_cls(self._parent)
        return dialog

    def yes_or_no(self, title:str, message:str) -> bool:
        """ Present a yes/no dialog and return the user's response as a bool. """
        yes, no = QMessageBox.Yes, QMessageBox.No
        button = QMessageBox.question(self._parent, title, message, yes | no)
        return button == yes

    def open_file(self, title="Open File", file_exts="", start_dir=".") -> str:
        """ Present a modal dialog for the user to select a file to open.
            Return the selected filename, or an empty string on cancel. """
        return QFileDialog.getOpenFileName(self._parent, title, start_dir, _filter_str(file_exts))[0]

    def open_files(self, title="Open Files", file_exts="", start_dir=".") -> List[str]:
        """ Present a modal dialog for the user to select multiple files to open.
            Return a list of selected filenames, or an empty list on cancel. """
        return QFileDialog.getOpenFileNames(self._parent, title, start_dir, _filter_str(file_exts))[0]

    def save_file(self, title="Save File", file_exts="", start_dir=".") -> str:
        """ Present a modal dialog for the user to select a file to save.
            Return the selected filename, or an empty string on cancel. """
        return QFileDialog.getSaveFileName(self._parent, title, start_dir, _filter_str(file_exts))[0]
