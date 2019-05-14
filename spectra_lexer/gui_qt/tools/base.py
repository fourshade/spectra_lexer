""" Base module for a Qt dialog framework with callbacks. """

from functools import partial
from typing import Callable, Hashable

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDialog, QDialogButtonBox, QLayout, QWidget

from ..window import GUI
from spectra_lexer.core import Component


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


class QtTool(Component,
             GUI.Window):
    """ Qt-based dialog tool. Tracks a dialog object so that no more than one ever exists. """

    DIALOG_CLASS: type = QDialog  # Dialog class to instantiate (only one at a time)

    _dialog: QDialog = None  # Previous dialog object. Must be set to None on deletion.

    def new_dialog(self, *args, persistent=False) -> None:
        """ Respond to a command to open a new dialog. If a dialog exists but is not persistent, destroy it. """
        dlg = self._dialog
        if dlg is not None and not persistent:
            dlg.close()
            dlg = None
        # If no dialog exists (including because we destroyed it), make a new one.
        if dlg is None:
            dlg = self._dialog = self.DIALOG_CLASS(self.window, *args)
        # Show the new/old dialog in any case.
        dlg.show()


class QtCommandTool(QtTool):

    def new_dialog(self, submit_command:Hashable=None, *args) -> None:
        """ Some dialogs need to submit information back to the original component.
            Use a partial function with the given callback to do this. """
        super().new_dialog(partial(self.engine_call, submit_command), *args)
