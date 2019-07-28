from typing import Callable, List

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDialog, QDialogButtonBox, QFileDialog, QLayout, QWidget


def load_files_dialog(parent:QWidget, res_type:str, *fmts:str) -> List[str]:
    """ Present a modal dialog to select files with an extension in <fmts> for loading.
        Return the file selection list, or an empty list if cancelled. """
    title = f"Load {res_type.title()}"
    filter_msg = f"Supported files (*{' *'.join(fmts)})"
    return QFileDialog.getOpenFileNames(parent, title, ".", filter_msg)[0]


class ToolDialog(QDialog):
    """ Base class for a Qt dialog window object used by a GUI tool. """

    TITLE: str = "Untitled"   # Dialog window title string.
    SIZE: tuple = (200, 200)  # Dimensions in pixels: (width, height).

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


class DialogContainer(dict):
    """ Dict for Qt-based dialog container. Tracks dialog objects so that no more than one of each ever exists. """

    def open(self, d_cls:type, *args, persistent:bool=False, **kwargs) -> None:
        """ If a dialog does not exist or is not persistent, open a new one. """
        if d_cls not in self or not persistent:
            # If a dialog does exist but is not persistent, destroy the old one.
            if d_cls in self:
                self.close(d_cls)
            self[d_cls] = d_cls(*args, **kwargs)
        # Show the new/old dialog in any case.
        self[d_cls].show()

    def close(self, d_cls:type) -> None:
        """ Close an existing dialog and delete the reference (which may destroy it). """
        self[d_cls].close()
        del self[d_cls]
