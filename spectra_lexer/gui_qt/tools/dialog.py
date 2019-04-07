""" Base module for modal (one-shot) dialogs and a framework for more complicated ones with callbacks. """

from typing import Callable, Sequence

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDialog, QDialogButtonBox, QFileDialog, QLayout, QMessageBox, QWidget


def FileDialog(parent:QFileDialog, callback:Callable, title:str, fmts_msg:str, fmts:Sequence[str]) -> None:
    """ Create a modal file open dialog and send a file selection to the callback.
        If the dialog is cancelled, send an empty list. """
    filter_msg = f"{fmts_msg} (*{' *'.join(fmts)})"
    callback(QFileDialog.getOpenFileName(parent, title, ".", filter_msg)[0])


def MessageDialog(parent:QMessageBox, callback:Callable, title:str, message:str,
                  main_button:str="OK", *other_buttons:str) -> None:
    """ Create a simple modal message dialog. There is always at least one button: <main_button>.
        After that, each string in <other_buttons> adds another button going left to right.
        Send the string on the button that was chosen, or the rightmost one if the dialog was closed another way. """
    dialog = QMessageBox(parent)
    dialog.setWindowTitle(title)
    dialog.setText(message)
    all_buttons = main_button, *other_buttons
    button_objects = [dialog.addButton(b, QMessageBox.AcceptRole) for b in all_buttons]
    dialog.setDefaultButton(button_objects[0])
    dialog.exec_()
    selection = dialog.clickedButton()
    try:
        callback(all_buttons[button_objects.index(selection)])
    except (KeyError, ValueError):
        callback(all_buttons[-1])


class ToolDialog(QDialog):
    """ Base class for a Qt dialog window object used by a GUI tool. """

    TITLE: str = "Untitled"   # Dialog window title string.
    SIZE: tuple = (200, 200)  # Dimensions in pixels: (width, height).

    callback: Callable  # A callback to return any necessary output to the parent.

    def __init__(self, parent:QWidget, callback:Callable, *args):
        """ Create the root UI dialog window and layout, then set the callback. """
        super().__init__(parent, Qt.CustomizeWindowHint | Qt.Dialog | Qt.WindowTitleHint | Qt.WindowCloseButtonHint)
        self.setWindowTitle(self.TITLE)
        self.resize(*self.SIZE)
        self.setMinimumSize(*self.SIZE)
        self.setSizeGripEnabled(False)
        self.callback = callback
        self.make_layout(*args)

    def make_layout(self, *args) -> None:
        """ Subclasses create and populate a layout with widgets here. """
        raise NotImplementedError


class FormDialog(ToolDialog):
    """ A GUI tool dialog class for a submission form. Has standard buttons and returns useful output on accept. """

    def make_layout(self,  *args) -> None:
        """ Get the subclass layout, add the standard buttons at the bottom, and connect basic signals. """
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
