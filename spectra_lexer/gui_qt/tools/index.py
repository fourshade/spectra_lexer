from PyQt5.QtCore import pyqtSignal, QObject, Qt
from PyQt5.QtWidgets import QDialog, QDialogButtonBox, QLabel, QSlider, QToolTip, QVBoxLayout

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


class IndexSizeTool(QObject):
    """ Qt index dialog tool. Adds an interactive slider that submits a positive number on accept, or 0 on cancel. """

    _sig_accept = pyqtSignal([int])  # Signal to return the index size on dialog accept.

    def __init__(self, dialog:QDialog) -> None:
        super().__init__()
        self._dialog = dialog                   # Base dialog object.
        self._slider = IndexSizeSlider(dialog)  # Horizontal slider widget.
        self.call_on_size_accept = self._sig_accept.connect
        dialog.tool_ref = self

    def display(self) -> None:
        """ Fill out the dialog with widgets and show it. """
        dialog = self._dialog
        heading_label = QLabel(dialog)
        heading_label.setWordWrap(True)
        heading_label.setText(SIZE_DESCRIPTIONS)
        slider = self._slider
        slider.setMinimum(_INFO.MINIMUM_SIZE)
        slider.setMaximum(_INFO.MAXIMUM_SIZE)
        slider.setValue(_INFO.MEDIUM_SIZE)
        slider.setOrientation(Qt.Horizontal)
        slider.setTickPosition(QSlider.TicksBelow)
        slider.setTickInterval(1)
        desc_label = QLabel(dialog)
        desc_label.setWordWrap(True)
        desc_label.setText(SIZE_WARNING)
        button_box = QDialogButtonBox(dialog)
        button_box.setStandardButtons(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.setCenterButtons(True)
        button_box.accepted.connect(self._check_accept)
        button_box.rejected.connect(dialog.reject)
        layout = QVBoxLayout(dialog)
        layout.addWidget(heading_label)
        layout.addWidget(slider)
        layout.addWidget(desc_label)
        layout.addWidget(button_box)
        dialog.show()

    def _check_accept(self) -> None:
        """ Emit the slider position on accept and close the window. """
        value = self._slider.value()
        self._sig_accept.emit(value)
        self._dialog.accept()
