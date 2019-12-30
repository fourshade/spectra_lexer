from typing import Sequence

from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtWidgets import QDialog, QDialogButtonBox, QLabel, QSlider, QToolTip, QVBoxLayout


INDEX_STARTUP_MESSAGE = """<p>
In order to cross-reference examples of specific steno rules, this program must create an index
using your Plover dictionary. The default file size is around 10 MB, and can take anywhere
between 5 seconds and 5 minutes depending on the speed of your machine and hard disk.
Would you like to create one now? You will not be asked again.
</p><p>
(If you cancel, all other features will still work. You can always create the index later from
the Tools menu, and can expand it from the default size as well if it is not sufficient).
</p>"""

SIZE_WARNING = """<p align='justify'>
An extremely large index is not necessarily more useful.
The index is created from the Plover dictionary, which is very large
(about 150,000 translations) with many useless and even erroneous entries.
As the index grows, so does the loading time,
and past a certain point the garbage will start to crowd out useful information.
Unless you are doing batch analysis, there is little benefit to a maximum-sized index.
</p>"""

SIZE_DESCRIPTION_FMT = """
Please choose a size for the new index.<br><br>
size = {}: includes nothing.<br><br>
size = {}: fast index with relatively simple words.<br><br>
size = {}: average-sized index (default).<br><br>
size = {}: slower index with more advanced words.<br><br>
size = {}: includes everything.
"""


class IndexSizeSlider(QSlider):
    """ Qt interactive slider that displays its value in a tooltip when moved. """

    def sliderChange(self, change:int) -> None:
        """ Show a tooltip with the current numerical value when the slider is moved. """
        if change == self.SliderValueChange:
            global_pos = self.parentWidget().pos() + self.pos()
            QToolTip.showText(global_pos, str(self.value()), self)
        super().sliderChange(change)


class IndexSizeDialog(QDialog):
    """ Qt index dialog tool. Adds an interactive slider that submits a positive number on accept, or 0 on cancel. """

    _sig_accept = pyqtSignal([int])  # Signal to return the index size on dialog accept.

    def __init__(self, *args) -> None:
        super().__init__(*args)
        self.setWindowTitle("Choose Index Size")
        self.set_size(360, 320)
        self._heading = heading = QLabel(self)         # Index size description label.
        heading.setWordWrap(True)
        self._slider = slider = IndexSizeSlider(self)  # Horizontal slider widget.
        slider.setOrientation(Qt.Horizontal)
        slider.setTickPosition(QSlider.TicksBelow)
        slider.setTickInterval(1)
        desc_label = QLabel(self)
        desc_label.setWordWrap(True)
        desc_label.setText(SIZE_WARNING)
        button_box = QDialogButtonBox(self)
        button_box.setStandardButtons(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.setCenterButtons(True)
        button_box.accepted.connect(self._check_accept)
        button_box.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addWidget(heading)
        layout.addWidget(slider)
        layout.addWidget(desc_label)
        layout.addWidget(button_box)
        self.call_on_size_accept = self._sig_accept.connect

    def set_size(self, width:int, height:int) -> None:
        """ Set the minimum size of the window and resize it to be that. """
        self.resize(width, height)
        self.setMinimumSize(width, height)
        self.setMaximumSize(width, height)

    def setup(self, sizes:Sequence[int]) -> None:
        """ Show info for a sequence of 5 index sizes from smallest to largest. """
        assert len(sizes) == 5
        self._heading.setText(SIZE_DESCRIPTION_FMT.format(*sizes))
        self._slider.setMinimum(sizes[0])
        self._slider.setMaximum(sizes[4])
        self._slider.setValue(sizes[2])

    def _check_accept(self) -> None:
        """ Emit the slider position on accept and close the window. """
        value = self._slider.value()
        self._sig_accept.emit(value)
        self.accept()
