""" Wrapper functions for various Qt file selection dialogs. """

from typing import List

from PyQt5.QtWidgets import QFileDialog


def _filter_str(file_exts="") -> str:
    """ Return a file dialog filter string based on file extensions (without the dot).
        If <file_exts> is empty, return a filter string matching any file.
        Multiple file extensions may be delimited by a | character. """
    if not file_exts:
        return "All files (*.*)"
    filters = [f"{ext.upper()} files (*.{ext})" for ext in file_exts.split("|")]
    return ";;".join(filters)


def open_file_dialog(parent=None, title="Open File", file_exts="", start_dir=".") -> str:
    """ Present a modal dialog for the user to select a file to open.
        Return the selected filename, or an empty string on cancel. """
    return QFileDialog.getOpenFileName(parent, title, start_dir, _filter_str(file_exts))[0]


def open_files_dialog(parent=None, title="Open Files", file_exts="", start_dir=".") -> List[str]:
    """ Present a modal dialog for the user to select multiple files to open.
        Return a list of selected filenames, or an empty list on cancel. """
    return QFileDialog.getOpenFileNames(parent, title, start_dir, _filter_str(file_exts))[0]


def save_file_dialog(parent=None, title="Save File", file_exts="", start_dir=".") -> str:
    """ Present a modal dialog for the user to select a file to save.
        Return the selected filename, or an empty string on cancel. """
    return QFileDialog.getSaveFileName(parent, title, start_dir, _filter_str(file_exts))[0]
