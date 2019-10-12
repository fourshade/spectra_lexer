from typing import List, Type
from weakref import WeakValueDictionary

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDialog, QFileDialog, QMessageBox, QWidget


class ModalDialogGenerator:
    """ Opens common modal dialogs under a parent widget (usually the main window) and returns their results. """

    def __init__(self, parent:QWidget=None) -> None:
        self._parent = parent  # All GUI dialogs must be children of some widget.

    def yes_or_no(self, title:str, message:str) -> bool:
        """ Present a yes/no dialog and return the user's response as a bool. """
        yes, no = QMessageBox.Yes, QMessageBox.No
        button = QMessageBox.question(self._parent, title, message, yes | no)
        return button == yes

    def open_file(self, title="Open File", file_ext="") -> str:
        """ Present a modal dialog for the user to select a file to open.
            Return the selected filename, or an empty string on cancel. """
        return QFileDialog.getOpenFileName(self._parent, title, ".", self._filter_str(file_ext))[0]

    def open_files(self, title="Open Files", file_ext="") -> List[str]:
        """ Present a modal dialog for the user to select multiple files to open.
            Return a list of selected filenames, or an empty list on cancel. """
        return QFileDialog.getOpenFileNames(self._parent, title, ".", self._filter_str(file_ext))[0]

    @staticmethod
    def _filter_str(file_ext="") -> str:
        """ Return a file dialog filter string based on a file extension. It should not include the dot.
            If <file_ext> is empty, return a filter string matching any file. """
        if not file_ext:
            return "All files (*.*)"
        return f"{file_ext.upper()} files (*.{file_ext})"


class ToolDialog(QDialog):
    """ Abstract base class for a Qt dialog object used by a GUI tool. """

    title: str   # Starting dialog window title.
    width: int   # Starting window width in pixels.
    height: int  # Starting window height in pixels.

    def setup(self, *args, **kwargs) -> None:
        raise NotImplementedError

    def __init__(self, *args) -> None:
        """ Set the most basic properties of the window: the title string and its dimensions in pixels. """
        super().__init__(*args)
        self.setWindowTitle(self.title)
        self.resize(self.width, self.height)
        self.setMinimumSize(self.width, self.height)
        self.setSizeGripEnabled(False)


class SingletonDialogGenerator:
    """ Constructs dialogs with classes restricted to one open instance each. New instances will replace old ones. """

    _WINDOW_FLAGS = Qt.CustomizeWindowHint | Qt.Dialog | Qt.WindowTitleHint | Qt.WindowCloseButtonHint

    def __init__(self, parent:QWidget=None) -> None:
        self._parent = parent                          # All GUI dialogs must be children of some widget.
        self._dialogs_by_type = WeakValueDictionary()  # Contains the current instance of each dialog class in use.

    def open_dialog(self, dialog_cls:Type[ToolDialog], *args, **kwargs) -> None:
        """ If a previous instance of <dialog's> class is open, set focus on it. Otherwise make a new dialog. """
        dialog = self._dialogs_by_type.get(dialog_cls)
        if dialog is None or dialog.isHidden():
            dialog = dialog_cls(self._parent, self._WINDOW_FLAGS)
            dialog.setup(*args, **kwargs)
            self._dialogs_by_type[dialog_cls] = dialog
        dialog.show()
        dialog.activateWindow()
