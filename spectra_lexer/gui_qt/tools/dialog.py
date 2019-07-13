from typing import Callable

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDialog, QWidget, QDialogButtonBox, QLayout


class ToolDialog(QDialog):
    """ Base class for a Qt dialog window object used by a GUI tool. """

    TITLE: str = "Untitled"   # Dialog window title string.
    SIZE: tuple = (200, 200)  # Dimensions in pixels: (width, height).

    def __init__(self, parent:QWidget, *args):
        """ Create the root UI dialog window and layout. """
        super().__init__(parent, Qt.CustomizeWindowHint | Qt.Dialog | Qt.WindowTitleHint | Qt.WindowCloseButtonHint)
        self.setWindowTitle(self.TITLE)
        self.resize(*self.SIZE)
        self.setMinimumSize(*self.SIZE)
        self.setSizeGripEnabled(False)
        self.make_layout(*args)

    def make_layout(self, *args) -> None:
        """ Subclasses create and populate a layout with widgets here. """
        raise NotImplementedError


class FormDialog(ToolDialog):
    """ A GUI tool dialog class for a submission form. Has standard buttons and returns useful output on accept. """

    callback: Callable  # A callback to return any necessary output to the parent.

    def make_layout(self, callback:Callable=None, *args) -> None:
        """ Set the callback, get the subclass layout, and add standard buttons at the bottom. """
        self.callback = callback
        layout = self.new_layout(*args)
        w_buttons = QDialogButtonBox(self)
        w_buttons.setStandardButtons(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        w_buttons.setCenterButtons(True)
        w_buttons.accepted.connect(self.accept)
        w_buttons.rejected.connect(self.reject)
        layout.addWidget(w_buttons)

    def new_layout(self, *args) -> QLayout:
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
            return super().accept()


class DialogContainer:
    """ Qt-based dialog container. Tracks a dialog object so that no more than one ever exists. """

    _dialog_cls: type        # Dialog class to instantiate (only one at a time).
    _is_persistent: bool     # If True, new dialog requests will not destroy an existing dialog.
    _dialog = None           # Previous dialog object. Must be set to None on deletion.

    def __init__(self, dialog_cls:type, persistent:bool=False):
        self._dialog_cls = dialog_cls
        self._is_persistent = persistent

    def __bool__(self) -> bool:
        return self._dialog is not None

    def __getattr__(self, attr:str):
        return getattr(self._dialog, attr)

    def open(self, *args) -> None:
        """ Respond to a command to open a new dialog. If a dialog exists but is not persistent, destroy it. """
        if self and not self._is_persistent:
            self.close()
        # If no dialog exists (including because we destroyed it), make a new one.
        if not self:
            self._dialog = self._dialog_cls(*args)
        # Show the new/old dialog in any case.
        self.show()

    def close(self):
        self._dialog.close()
        self._dialog = None
