from typing import Callable

from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtWidgets import QDialogButtonBox, QLabel, QSlider, QToolTip, QVBoxLayout

from .dialog import ToolDialog

from spectra_lexer.steno import TranslationSizeFilter as _INFO

SIZE_WARNING = """<p align='justify'>
An extremely large index is not necessarily more useful.
The index is created from the Plover dictionary, which is very large
(about 150,000 translations) with many useless and even erroneous entries.
As the index grows, so does the loading time,
and past a certain point the garbage will start to crowd out useful information.
Unless you are doing batch analysis, there is little benefit to a maximum-sized index.
</p>"""

SIZE_DESCRIPTIONS = f"""
Please choose a size for the new index.<br><br>
size = {_INFO.MINIMUM_SIZE}: includes nothing.<br><br>
size = {_INFO.SMALL_SIZE  }: fast index with relatively simple words.<br><br>
size = {_INFO.MEDIUM_SIZE }: average-sized index (default).<br><br>
size = {_INFO.LARGE_SIZE  }: slower index with more advanced words.<br><br>
size = {_INFO.MAXIMUM_SIZE}: includes everything."""


class IndexSizeSlider(QSlider):
    """ Qt interactive slider that displays its value in a tooltip when moved. """

    def sliderChange(self, change:int) -> None:
        """ Show a tooltip with the current numerical value when the slider is moved. """
        if change == self.SliderValueChange:
            global_pos = self.parentWidget().pos() + self.pos()
            QToolTip.showText(global_pos, str(self.value()), self)
        super().sliderChange(change)


class IndexSizeDialog(ToolDialog):
    """ Qt dialog window with an interactive slider that submits a positive number on accept, or 0 on cancel. """

    _sig_accept = pyqtSignal([int])  # Signal to return the index size on dialog accept.

    title = "Choose Index Size"
    width = 360
    height = 320

    def __init__(self, *args) -> None:
        super().__init__(*args)
        self._slider = IndexSizeSlider(self)  # Horizontal slider widget.

    def setup(self, size_callback:Callable[[int], None]) -> None:
        heading_label = QLabel(self)
        heading_label.setWordWrap(True)
        heading_label.setText(SIZE_DESCRIPTIONS)
        self._slider.setMinimum(_INFO.MINIMUM_SIZE)
        self._slider.setMaximum(_INFO.MAXIMUM_SIZE)
        self._slider.setValue(_INFO.MEDIUM_SIZE)
        self._slider.setOrientation(Qt.Horizontal)
        self._slider.setTickPosition(QSlider.TicksBelow)
        self._slider.setTickInterval(1)
        desc_label = QLabel(self)
        desc_label.setWordWrap(True)
        desc_label.setText(SIZE_WARNING)
        button_box = QDialogButtonBox(self)
        button_box.setStandardButtons(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.setCenterButtons(True)
        button_box.accepted.connect(self.check_accept)
        button_box.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addWidget(heading_label)
        layout.addWidget(self._slider)
        layout.addWidget(desc_label)
        layout.addWidget(button_box)
        self._sig_accept.connect(size_callback)

    def check_accept(self) -> None:
        """ Emit the slider position on accept and close the window. """
        value = self._slider.value()
        self._sig_accept.emit(value)
        self.accept()
