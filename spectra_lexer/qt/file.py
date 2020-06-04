""" Wrapper functions for various Qt file selection dialogs. """

from typing import List

from PyQt5.QtWidgets import QFileDialog


def _filter_str(file_ext="") -> str:
    """ Return a file dialog filter string based on a file extension. It should not include the dot.
        If <file_ext> is empty, return a filter string matching any file. """
    if not file_ext:
        return "All files (*.*)"
    return f"{file_ext.upper()} files (*.{file_ext})"


def open_file_dialog(parent=None, title="Open File", file_ext="", start_dir=".") -> str:
    """ Present a modal dialog for the user to select a file to open.
        Return the selected filename, or an empty string on cancel. """
    return QFileDialog.getOpenFileName(parent, title, start_dir, _filter_str(file_ext))[0]


def open_files_dialog(parent=None, title="Open Files", file_ext="", start_dir=".") -> List[str]:
    """ Present a modal dialog for the user to select multiple files to open.
        Return a list of selected filenames, or an empty list on cancel. """
    return QFileDialog.getOpenFileNames(parent, title, start_dir, _filter_str(file_ext))[0]


def save_file_dialog(parent=None, title="Save File", file_ext="", start_dir=".") -> str:
    """ Present a modal dialog for the user to select a file to save.
        Return the selected filename, or an empty string on cancel. """
    return QFileDialog.getSaveFileName(parent, title, start_dir, _filter_str(file_ext))[0]
