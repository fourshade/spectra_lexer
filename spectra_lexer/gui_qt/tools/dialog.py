""" Base module for modal (one-shot) dialogs and a framework for more complicated ones with callbacks. """

from typing import Callable

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDialog, QDialogButtonBox, QMessageBox, QWidget


def MessageDialog(parent:QMessageBox, title:str, message:str, main_button:str="OK", *other_buttons:str) -> str:
    """ Create a simple modal message dialog. There is always at least one button: <main_button>.
        After that, each string in <other_buttons> adds another button going left to right.
        Return the string on the button that was chosen, or the rightmost one if the dialog was closed another way. """
    dialog = QMessageBox(parent)
    dialog.setWindowTitle(title)
    dialog.setText(message)
    all_buttons = main_button, *other_buttons
    button_objects = [dialog.addButton(b, QMessageBox.AcceptRole) for b in all_buttons]
    dialog.setDefaultButton(button_objects[0])
    dialog.exec_()
    selection = dialog.clickedButton()
    try:
        return all_buttons[button_objects.index(selection)]
    except (KeyError, ValueError):
        return all_buttons[-1]


class ToolDialog(QDialog):
    """ Base class for a Qt dialog window object used by a GUI tool. """

    _submit_cb: Callable  # A callback to return any necessary output values to the parent.

    def __init__(self, parent:QWidget, submit_cb:Callable, title:str, width:int, height:int):
        """ Create the root UI elements and set the callback. """
        super().__init__(parent, Qt.CustomizeWindowHint | Qt.Dialog | Qt.WindowTitleHint | Qt.WindowCloseButtonHint)
        self.setWindowTitle(title)
        self._submit_cb = submit_cb
        self.resize(width, height)
        self.setMinimumSize(width, height)
        self.setSizeGripEnabled(False)

    def make_buttons(self) -> QDialogButtonBox:
        """ Make the standard buttons and connect basic signals. """
        w_buttons = QDialogButtonBox(self)
        w_buttons.setStandardButtons(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        w_buttons.setCenterButtons(True)
        w_buttons.accepted.connect(self.accept)
        w_buttons.rejected.connect(self.reject)
        return w_buttons

    def accept(self) -> None:
        """ Submit the return value to the parent via the saved callback (unless it is None). """
        value = self.submit()
        if value is not None:
            self._submit_cb(value)
            return super().accept()

    def submit(self):
        """ The callback returns one argument to the parent. Subclasses return that here, or None to cancel. """
        raise NotImplementedError
