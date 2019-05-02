""" Base module for modal (one-shot) dialogs and a framework for more complicated ones with callbacks. """

from typing import Callable

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDialog, QDialogButtonBox,  QLabel, QLayout, QMessageBox, QSlider, QToolTip, QVBoxLayout, \
    QWidget


def MessageDialog(parent:QMessageBox, title:str, message:str, main_button:str="OK", *other_buttons:str) -> str:
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
        return all_buttons[button_objects.index(selection)]
    except (KeyError, ValueError):
        return all_buttons[-1]


class ToolDialog(QDialog):
    """ Base class for a Qt dialog window object used by a GUI tool. """

    TITLE: str = "Untitled"   # Dialog window title string.
    SIZE: tuple = (200, 200)  # Dimensions in pixels: (width, height).

    callback: Callable  # A callback to return any necessary output to the parent.

    def __init__(self, parent:QWidget, callback:Callable=None, *args):
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

    def make_layout(self, *args) -> None:
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


class SliderDialog(FormDialog):
    """ Qt dialog window object with labels and a single interactive slider. """

    slider: QSlider = None  # Horizontal slider.

    def new_layout(self, upper_text:str, lower_text:str, slider_range:tuple) -> QLayout:
        minimum, default, maximum = slider_range
        layout = QVBoxLayout(self)
        heading_label = QLabel(self)
        heading_label.setWordWrap(True)
        heading_label.setText(upper_text)
        self.slider = QSlider(self)
        self.slider.setMinimum(minimum)
        self.slider.setMaximum(maximum)
        self.slider.setValue(default)
        self.slider.setOrientation(Qt.Horizontal)
        self.slider.setTickPosition(QSlider.TicksBelow)
        self.slider.setTickInterval(1)
        self.slider.valueChanged.connect(self.new_slider_value)
        desc_label = QLabel(self)
        desc_label.setWordWrap(True)
        desc_label.setText(lower_text)
        layout.addWidget(heading_label)
        layout.addWidget(self.slider)
        layout.addWidget(desc_label)
        return layout

    def submit(self) -> int:
        """ Return the slider position on submit. """
        return self.slider.value()

    # Slots
    def new_slider_value(self, value:int) -> None:
        """ Show a tooltip with the current numerical value when the slider is moved. """
        QToolTip.showText(self.pos() + self.slider.pos(), str(value), self.slider)
