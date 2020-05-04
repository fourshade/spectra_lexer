from typing import List, Optional, Type
from weakref import WeakValueDictionary

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtWidgets import QDialog, QFileDialog, QMainWindow, QMessageBox


def _filter_str(file_ext="") -> str:
    """ Return a file dialog filter string based on a file extension. It should not include the dot.
        If <file_ext> is empty, return a filter string matching any file. """
    if not file_ext:
        return "All files (*.*)"
    return f"{file_ext.upper()} files (*.{file_ext})"


class WindowController:
    """ Wrapper class with methods for manipulating the main window.
        Also opens common modal dialogs and returns their results. """

    _DEFAULT_DIALOG_FLAGS = Qt.CustomizeWindowHint | Qt.Dialog | Qt.WindowTitleHint | Qt.WindowCloseButtonHint

    def __init__(self, w_window:QMainWindow) -> None:
        self._w_window = w_window                     # Main Qt window. All dialogs must be children of this widget.
        self._dialogs_by_cls = WeakValueDictionary()  # Contains the current instance of each dialog class.
        self.close = w_window.close

    def show(self) -> None:
        """ Show the window, move it in front of other windows, and activate focus. """
        self._w_window.show()
        self._w_window.activateWindow()
        self._w_window.raise_()

    def set_icon(self, data:bytes) -> None:
        """ Set the main window icon from a raw bytes object containing an image in some standard format.
            PNG and SVG formats are known to work. """
        pixmap = QPixmap()
        pixmap.loadFromData(data)
        icon = QIcon(pixmap)
        self._w_window.setWindowIcon(icon)

    def has_focus(self) -> bool:
        """ Return True if the window (or something in it) currently has keyboard focus. """
        return self._w_window.isActiveWindow()

    def open_dialog(self, dlg_cls:Type[QDialog], flags=_DEFAULT_DIALOG_FLAGS) -> Optional[QDialog]:
        """ If a previous <dlg_cls> is open, set focus on it and return None, otherwise return a new one. """
        dialog = self._dialogs_by_cls.get(dlg_cls)
        if dialog is not None and not dialog.isHidden():
            dialog.show()
            dialog.activateWindow()
            return None
        dialog = self._dialogs_by_cls[dlg_cls] = dlg_cls(self._w_window, flags)
        return dialog

    def yes_or_no(self, title:str, message:str) -> bool:
        """ Present a yes/no dialog and return the user's response as a bool. """
        yes, no = QMessageBox.Yes, QMessageBox.No
        button = QMessageBox.question(self._w_window, title, message, yes | no)
        return button == yes

    def open_file(self, title="Open File", start_dir=".", file_ext="") -> str:
        """ Present a modal dialog for the user to select a file to open.
            Return the selected filename, or an empty string on cancel. """
        return QFileDialog.getOpenFileName(self._w_window, title, start_dir, _filter_str(file_ext))[0]

    def open_files(self, title="Open Files", start_dir=".", file_ext="") -> List[str]:
        """ Present a modal dialog for the user to select multiple files to open.
            Return a list of selected filenames, or an empty list on cancel. """
        return QFileDialog.getOpenFileNames(self._w_window, title, start_dir, _filter_str(file_ext))[0]
