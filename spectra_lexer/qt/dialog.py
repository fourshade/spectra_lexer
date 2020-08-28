from typing import Callable, List
from weakref import WeakValueDictionary

from PyQt5.QtWidgets import QDialog, QFileDialog, QMessageBox, QWidget

DialogOpener = Callable[[], QDialog]


def _filter_str(file_exts="") -> str:
    """ Return a file dialog filter string based on file extensions (without the dot).
        If <file_exts> is empty, return a filter string matching any file.
        Multiple file extensions may be delimited by a | character. """
    if not file_exts:
        return "All files (*.*)"
    filters = [f"{ext.upper()} files (*.{ext})" for ext in file_exts.split("|")]
    return ";;".join(filters)


class DialogManager:
    """ Opens and tracks Qt dialogs. """

    def __init__(self, parent:QWidget) -> None:
        self._parent = parent                  # All dialogs will be children of this widget.
        self._dialogs = WeakValueDictionary()  # Tracks a single instance of each dialog by its opener.

    def attach(self, dialog:QDialog) -> None:
        """ Attach <dialog> to our parent, preserving its window flags. """
        flags = dialog.windowFlags()
        dialog.setParent(self._parent)
        dialog.setWindowFlags(flags)

    def open_unique(self, opener:DialogOpener) -> None:
        """ If a previous dialog is open, set focus on it, otherwise open a new one using <opener>. """
        key = getattr(opener, '__qualname__', id(opener))
        dialog = self._dialogs.get(key)
        if dialog is not None and not dialog.isHidden():
            dialog.activateWindow()
        else:
            dialog = self._dialogs[key] = opener()
            self.attach(dialog)
            dialog.show()

    def yes_or_no(self, title:str, message:str) -> bool:
        """ Present a modal yes/no dialog and return the user's response as True/False. """
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
