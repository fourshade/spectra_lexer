from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QLabel, QLayout, QMessageBox, QSlider, QToolTip, QVBoxLayout

from .base import FormDialog, GUIQtTool
from spectra_lexer.gui import IndexTool


class IndexDialog(FormDialog):
    """ Qt dialog window with an interactive slider that submits a positive number on accept, or 0 on cancel. """

    TITLE = "Choose Index Size"
    SIZE = (360, 320)

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


class GUIQtIndexTool(GUIQtTool, IndexTool):
    """ Controls user-based index creation. """

    DIALOG_CLASS = IndexDialog

    def confirm_new_startup_index(self, question:str) -> bool:
        """ Create a simple modal message dialog and return the user's selection yes/no. """
        button = QMessageBox.question(self.window, "Make Index", question, QMessageBox.Yes | QMessageBox.No)
        return button == QMessageBox.Yes
