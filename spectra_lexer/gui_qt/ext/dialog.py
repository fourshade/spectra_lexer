from typing import Callable, List

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDialog, QDialogButtonBox, QFileDialog, QLayout, QWidget


class FileDialog:
    """ Utility class for modal file dialogs. """

    @classmethod
    def open(cls, *args) -> str:
        """ Open a file dialog to select a single file. Return None if cancelled. """
        return cls._dialog(QFileDialog.getOpenFileName, *args)

    @classmethod
    def open_all(cls, *args) -> List[str]:
        """ Open a file dialog to select a list of files. Return an empty list if cancelled. """
        return cls._dialog(QFileDialog.getOpenFileNames, *args)

    @classmethod
    def _dialog(cls, loader:Callable, parent:QWidget, title:str, *fmts:str):
        """ Present a modal dialog to select files with an extension in <fmts>. """
        filter_msg = f"Supported files (*{' *'.join(fmts)})"
        return loader(parent, title, ".", filter_msg)[0]


class ToolDialog(QDialog):
    """ Base class for a Qt dialog window object used by a GUI tool. No more than one of each subclass should exist. """

    TITLE: str = "Untitled"   # Dialog window title string.
    SIZE: tuple = (200, 200)  # Dimensions in pixels: (width, height).

    _LAST_INSTANCE: QDialog = None

    def __new__(cls, *args, **kwargs):
        """ If an old dialog exists, close it first and overwrite the reference (which may destroy it). """
        if cls._LAST_INSTANCE is not None:
            cls._LAST_INSTANCE.close()
        self = cls._LAST_INSTANCE = super().__new__(cls, *args, **kwargs)
        return self

    def __init__(self, parent:QWidget, *args, **kwargs):
        """ Create the root UI dialog window and layout. """
        super().__init__(parent, Qt.CustomizeWindowHint | Qt.Dialog | Qt.WindowTitleHint | Qt.WindowCloseButtonHint)
        self.setWindowTitle(self.TITLE)
        self.resize(*self.SIZE)
        self.setMinimumSize(*self.SIZE)
        self.setSizeGripEnabled(False)
        self.make_layout(*args, **kwargs)

    def make_layout(self, *args, **kwargs) -> None:
        """ Subclasses create and populate a layout with widgets here. """
        raise NotImplementedError


class FormDialog(ToolDialog):
    """ A GUI tool dialog class for a submission form. Has standard buttons and returns useful output on accept. """

    callback: Callable  # A callback to return any necessary output to the parent.

    def make_layout(self, callback:Callable=None, *args, **kwargs) -> None:
        """ Set the callback, get the subclass layout, and add standard buttons at the bottom. """
        self.callback = callback
        layout = self.new_layout(*args, **kwargs)
        w_buttons = QDialogButtonBox(self)
        w_buttons.setStandardButtons(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        w_buttons.setCenterButtons(True)
        w_buttons.accepted.connect(self.accept)
        w_buttons.rejected.connect(self.reject)
        layout.addWidget(w_buttons)

    def new_layout(self, *args, **kwargs) -> QLayout:
        """ Subclasses make a new layout and populate the top part with widgets here. """
        raise NotImplementedError

    def submit(self):
        """ The callback returns one argument to the parent. Subclasses return that here, or None to cancel. """
        raise NotImplementedError

    # Slots
    def accept(self) -> None:
        """ Submit the return value to the parent via the saved callback (unless it is None). """
        value = self.submit()
        if value is not None:
            self.callback(value)
            super().accept()
